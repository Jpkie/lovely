"""Agent Planner — 规则计划器 + LLM 计划器

架构: 用户自然语言任务 → Planner 输出 SkillCall(skill, args, confidence)
      → Orchestrator 调用 skill.build_steps(args, ctx) → Executor 执行

双模式:
  - RuleBasedPlanner: 关键词匹配 + 正则参数提取（无需 LLM）
  - LLMPlanner: LLM 推理选择 skill + 从文本提取参数（需要 LLM adapter）
"""

from abc import ABC, abstractmethod
from enum import Enum
import json
import re
import uuid
from typing import Any, Dict, List, Optional, Pattern
from pydantic import BaseModel, Field

from .schemas import AgentRequest, Message, ModelRole, Plan, PlanStep, PlannerOutput, SkillCall


# ────────────────── 数据模型 ──────────────────


class PlanStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    PLANNED = "planned"
    FAILED = "failed"


class SkillMatch(BaseModel):
    """规则匹配的中间结果"""

    skill_name: str = Field(description="匹配到的 skill 名称")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="匹配置信度")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="已提取的参数")


class PlannerConfig(BaseModel):
    """Planner 全局配置"""

    max_skills_per_task: int = Field(default=3, ge=1, le=10, description="单次任务最多调用几个 skill")
    enable_llm_planner: bool = Field(default=False, description="是否启用 LLM 规划")
    llm_model: Optional[str] = Field(default=None, description="LLM 模型名称")
    llm_temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="LLM 温度（低值更稳定）")


# ────────────────── 参数提取引擎 ──────────────────


class ParamExtractor:
    """从自然语言任务描述中提取结构化参数

    支持的提取维度：
      - 文件路径：/var/log/auth.log 等绝对/相对路径
      - 数量词："最近 200 条"、"前 50 个" 等
      - 日志类型关键词：auth / syslog / journal / btmp / message
      - 排序偏好：cpu / memory
      - 进程名称
      - 搜索关键词列表
      - SSH 配置路径
      - 开关选项（检查/不检查某项）
    """

    # ── 编译好的正则表 ──

    # 1) 绝对路径 /var/log/... 或 /etc/...
    _RE_ABS_PATH: Pattern[str] = re.compile(
        r'[/](?:var|etc|usr|opt|home|tmp|root|run)[/\w.\-]+', re.I
    )

    # 2) 带引号的路径
    _RE_QUOTED_PATH: Pattern[str] = re.compile(
        r'["\']([\w/.\-_]+)["\']', re.I
    )

    # 3) 数量词：最近 N 条 / 前 N 个 / 最后 N 行 / top N
    _RE_COUNT_ZH: Pattern[str] = re.compile(
        r'(?:最近|前|最后|top)[\s]*(\d+)[\s]*(?:条|个|行|项|条记录)?', re.I
    )
    _RE_COUNT_EN: Pattern[str] = re.compile(
        r'\b(?:last|first|top)\s*(\d+)\b', re.I
    )
    _RE_STANDALONE_NUM: Pattern[str] = re.compile(
        r'(?:读取|获取|显示|返回|列出|扫描)[^\d]{0,10}(\d{2,})[\s]*(?:条|个|行|项)?', re.I
    )

    # 4) 日志类型识别
    _RE_LOG_TYPE_AUTH: Pattern[str] = re.compile(
        r'\bauth(?:\.log)?\b|认证日志|登录日志|ssh.*log', re.I
    )
    _RE_LOG_TYPE_SYSLOG: Pattern[str] = re.compile(
        r'\bsyslog\b|系统日志|主日志', re.I
    )
    _RE_LOG_TYPE_JOURNAL: Pattern[str] = re.compile(
        r'\bjournal(?:ctl)?\b|journalctl|系统日志.*journal', re.I
    )
    _RE_LOG_TYPE_BTMP: Pattern[str] = re.compile(r'\bbtmp\b', re.I)
    _RE_LOG_TYPE_KERNEL: Pattern[str] = re.compile(r'\bdmesg\b|内核日志', re.I)
    _RE_LOG_TYPE_MESSAGE: Pattern[str] = re.compile(r'\bmessages\b', re.I)

    # 5) 排序方向
    _RE_SORT_CPU: Pattern[str] = re.compile(r'\bcpu\b.*排序|按\s*cpu|CPU\s*占用', re.I)
    _RE_SORT_MEMORY: Pattern[str] = re.compile(r'\b内存\b.*排序|按\s*内存|memory\s*(?:usage|sort)', re.I)

    # 6) 进程名
    _RE_PROCESS_NAME_EXPLICIT: Pattern[str] = re.compile(
        r'(?:进程[名\s]*[:：]|查找进程|搜索进程|进程名为?)\s*["\']?(\w[\w.\-]*)["\']?', re.I
    )
    _RE_PROCESS_NAME_AFTER_KEYWORD: Pattern[str] = re.compile(
        r'(?:进程)\s+(?:叫|名[字为]*)?\s*["\']?(\w[\w.\-]{2,})', re.I
    )

    # 7) 搜索关键词（逗号/顿号分隔）
    _RE_KEYWORDS: Pattern[str] = re.compile(
        r'(?:关键词?|关键字|搜索[词内容]*|包含)[:\s为]*([^\n,;，。]+?)(?:[,;，。]|$)', re.I
    )

    # 8) SSH 配置路径
    _RE_SSH_CONFIG_PATH: Pattern[str] = re.compile(
        r'sshd?[_\-]?config[:\s路径]*["\']?([\w/.\-]+)', re.I
    )

    # 9) 开关选项（是否检查某项）
    _RE_CHECK_OPTION: Pattern[str] = re.compile(
        r'(?:不?(?:检查|审计|跳过|忽略))\s*(用户|权限|文件|配置|sudo)', re.I
    )

    @classmethod
    def extract(cls, task: str, skill_name: str) -> Dict[str, Any]:
        """统一入口：根据 skill 类型从任务文本中提取所有可推断参数

        Args:
            task: 用户输入的自然语言任务
            skill_name: 已匹配到的目标 skill 名称

        Returns:
            提取出的参数字典，键与 Skill.parameters 定义对齐
        """
        params: Dict[str, Any] = {}

        # ── 通用提取（对所有 skill 都尝试）──

        # 路径提取
        path = cls._extract_path(task)
        if path:
            params["log_path" if "log" in skill_name else "_path"] = path

        # 数量提取
        count = cls._extract_count(task)
        if count is not None:
            params["_count"] = count

        # 关键词提取
        keywords = cls._extract_keywords(task)
        if keywords:
            params["keywords"] = keywords

        # ── 按 skill 类型专项提取 ──

        if skill_name == "log_investigation":
            params.update(cls._for_log_investigation(task, params))

        elif skill_name == "process_hunt":
            params.update(cls._for_process_hunt(task, params))

        elif skill_name == "ssh_audit":
            params.update(cls._for_ssh_audit(task, params))

        elif skill_name == "port_hunt":
            pass  # port_hunt 通常不需要参数

        elif skill_name == "host_triage":
            pass  # triage 是固定全量扫描

        elif skill_name == "fix_advisor":
            pass  # fix_advisor 依赖检测结果上下文

        # 清理内部临时 key
        params.pop("_path", None)
        params.pop("_count", None)

        return params

    # ── 通用提取方法 ──

    @classmethod
    def _extract_path(cls, task: str) -> Optional[str]:
        """优先绝对路径，其次引号包裹的路径"""
        m = cls._RE_ABS_PATH.search(task)
        if m:
            return m.group(0).strip()
        m = cls._RE_QUOTED_PATH.search(task)
        if m:
            return m.group(1).strip()
        return None

    @classmethod
    def _extract_count(cls, task: str) -> Optional[int]:
        """提取数量词中的数字"""
        for pattern in [cls._RE_COUNT_ZH, cls._RE_COUNT_EN, cls._RE_STANDALONE_NUM]:
            m = pattern.search(task)
            if m:
                return int(m.group(1))
        return None

    @classmethod
    def _extract_keywords(cls, task: str) -> Optional[List[str]]:
        """提取搜索关键词列表"""
        m = cls._RE_KEYWORDS.search(task)
        if m:
            raw = m.group(1).strip()
            # 支持中英文逗号分隔
            parts = re.split(r'[,;，、]', raw)
            return [p.strip() for p in parts if p.strip()]
        return None

    @classmethod
    def _extract_process_name(cls, task: str) -> Optional[str]:
        """提取目标进程名"""
        for pattern in [cls._RE_PROCESS_NAME_EXPLICIT, cls._RE_PROCESS_NAME_AFTER_KEYWORD]:
            m = pattern.search(task)
            if m:
                name = m.group(1).strip()
                # 过滤掉常见误匹配
                if name and name.lower() not in ("name", "process", "all"):
                    return name
        return None

    @classmethod
    def _detect_sort_by(cls, task: str) -> Optional[str]:
        """检测排序偏好"""
        if cls._RE_SORT_CPU.search(task):
            return "cpu"
        if cls._RE_SORT_MEMORY.search(task):
            return "memory"
        return None

    # ── 各 Skill 专项提取 ──

    @classmethod
    def _for_log_investigation(cls, task: str, base: Dict[str, Any]) -> Dict[str, Any]:
        """日志调查参数提取"""
        extra: Dict[str, Any] = {}

        # 如果没有显式给路径，按日志类型推断默认路径
        if "log_path" not in base:
            if cls._RE_LOG_TYPE_AUTH.search(task):
                extra["log_path"] = "/var/log/auth.log"
            elif cls._RE_LOG_TYPE_SYSLOG.search(task):
                extra["log_path"] = "/var/log/syslog"
            elif cls._RE_LOG_TYPE_JOURNAL.search(task):
                extra["log_path"] = "journal"  # 特殊标记，build_steps 会处理
            elif cls._RE_LOG_TYPE_BTMP.search(task):
                extra["log_path"] = "/var/log/btmp"
            elif cls._RE_LOG_TYPE_KERNEL.search(task):
                extra["log_path"] = "kernel"  # dmesg
            elif cls._RE_LOG_TYPE_MESSAGE.search(task):
                extra["log_path"] = "/var/log/messages"

        # 行数上限
        count = base.get("_count")
        if count is not None:
            extra["lines"] = count

        # journalctl 特殊处理
        if cls._RE_LOG_TYPE_JOURNAL.search(task) or "journal" in task.lower():
            extra["use_journal"] = True

        return extra

    @classmethod
    def _for_process_hunt(cls, task: str, base: Dict[str, Any]) -> Dict[str, Any]:
        """进程狩猎参数提取"""
        extra: Dict[str, Any] = {}

        # 目标进程名
        pname = cls._extract_process_name(task)
        if pname:
            extra["process_name"] = pname

        # 返回数量
        count = base.get("_count")
        if count is not None:
            extra["top_n"] = min(count, 200)  # 上限保护

        # 排序
        sort = cls._detect_sort_by(task)
        if sort:
            extra["sort_by"] = sort
        elif "高资源" in task or "高占用" in task:
            extra["sort_by"] = "memory"

        return extra

    @classmethod
    def _for_ssh_audit(cls, task: str, base: Dict[str, Any]) -> Dict[str, Any]:
        """SSH 审计参数提取"""
        extra: Dict[str, Any] = {}

        # 自定义 sshd_config 路径
        m = cls._RE_SSH_CONFIG_PATH.search(task)
        if m:
            extra["ssh_config_path"] = m.group(1).strip()

        # 开关选项检测
        if re.search(r'不?[检审]查?\s*用户', task, re.I):
            extra["check_users"] = not bool(re.search(r'^不', re.search(r'不?[检审]查?\s*用户', task, re.I).group(0)))
        if re.search(r'不?[检审]查?\s*(文件|权限)', task, re.I):
            match_obj = re.search(r'不?[检审]查?\s*(文件|权限)', task, re.I)
            if match_obj:
                extra["check_permissions"] = not match_obj.group(0).startswith("不")
        if re.search(r'不?[检审]查?\s*配置', task, re.I):
            match_obj = re.search(r'不?[检审]查?\s*配置', task, re.I)
            if match_obj:
                extra["check_config_file"] = not match_obj.group(0).startswith("不")

        return extra


# ────────────────── 抽象基类 ──────────────────


class BasePlanner(ABC):
    """Planner 抽象基类

    双接口设计:
      - plan()       → Plan (旧兼容，供 executor 直接消费)
      - plan_calls() → PlannerOutput (新版核心，输出带参数的 Skill 调用)
    """

    @abstractmethod
    async def plan(
        self,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        """生成执行计划 (Plan 对象，含有序步骤列表)"""
        ...

    async def plan_calls(
        self,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> PlannerOutput:
        """生成结构化 Skill 调用列表 (新版核心接口)

        默认实现：从 plan() 反推 calls（子类应覆写以提供更好的结果）
        """
        plan_result = await self.plan(request, available_skills, context)
        calls: List[SkillCall] = []
        seen: set = set()

        for step in plan_result.steps:
            sid = step.skill_id or step.skill_name
            if sid and sid not in seen:
                calls.append(SkillCall(skill=sid, args={}, confidence=0.8))
                seen.add(sid)

        return PlannerOutput(calls=calls, reasoning="从 plan() 反推 (fallback)")

    def _build_plan_from_output(
        self,
        output: PlannerOutput,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        """将 PlannerOutput.calls 通过 skill.build_steps() 展开为 Plan

        这是新旧架构的桥梁：Planner 只负责「选哪个 skill + 传什么参数」，
        具体执行步骤由 Skill 自己决定。
        """
        skill_map = {s.name: s for s in available_skills}
        steps: List[PlanStep] = []
        step_number = 1

        for call in output.calls:
            skill = skill_map.get(call.skill)
            if not skill:
                continue

            dynamic_steps = skill.build_steps(call.args, context)

            for s in dynamic_steps:
                steps.append(PlanStep(
                    id=s.id,
                    step_number=step_number,
                    description=f"[{skill.name}] {s.name}: {s.description}",
                    skill_id=skill.name,
                    tool_name=s.tool_name,
                    parameters=s.parameters,
                    status="pending",
                ))
                step_number += 1

        return Plan(
            id=str(uuid.uuid4()),
            request_id=request.id,
            steps=steps,
            status="planned",
        )


# ────────────────── 规则规划器 ──────────────────


class RuleBasedPlanner(BasePlanner):
    """基于关键词匹配 + 正则参数提取的规则规划器

    无需 LLM，纯本地推理。
    流程: 任务文本 → 关键词匹配 skill → ParamExtractor 提取参数 → 输出 PlannerOutput
    """

    # ── 关键词 → Skill 映射表 ──
    KEYWORD_MAPPING: Dict[str, List[str]] = {
        "host_triage": [
            "triage", "快速评估", "主机状态", "安全评估", "主机安全",
            "系统状态", "主机检查", "快速扫描", "全面检查", "健康检查",
        ],
        "log_investigation": [
            "日志", "log", "日志分析", "日志调查", "安全日志",
            "auth.log", "syslog", "journal", "登录失败", "暴力破解痕迹",
        ],
        "process_hunt": [
            "进程", "process", "进程分析", "进程调查", "可疑进程",
            "进程检查", "进程监控", "异常进程", "挖矿", "木马进程",
        ],
        "port_hunt": [
            "端口", "port", "端口扫描", "开放端口", "端口检查",
            "网络端口", "端口调查", "监听端口", "对外连接",
        ],
        "ssh_audit": [
            "ssh", "sshd", "ssh审计", "ssh安全", "ssh配置",
            "认证", "authorized_keys", "SSH加固", "远程登录",
        ],
        "fix_advisor": [
            "修复", "fix", "建议", "修复建议", "整改",
            "remediation", "修复步骤", "如何修复", "加固建议",
        ],
        "capability_check": [
            "环境探测", "能力检查", "环境检查", "capability", "环境信息",
        ],
        "hardening_baseline": [
            "基线", "baseline", "基线检查", "安全基线", " CIS ", "等保",
        ],
        "auto_remediation": [
            "自动修复", "auto remediation", "一键修复", "自动整改",
        ],
        "incident_timeline": [
            "时间线", "timeline", "事件时间线", "攻击链", "事件还原",
        ],
        "remediation_verification": [
            "验证修复", "验证效果", "remediation verify", "修复验证",
        ],
        "safe_config_patch": [
            "配置修补", "config patch", "安全配置修改", "配置修复",
        ],
    }

    def __init__(self, config: Optional[PlannerConfig] = None):
        self.config = config or PlannerConfig()

    # ── 匹配逻辑 ──

    def _match_skill_by_keywords(self, task: str) -> List[SkillMatch]:
        """基于关键词打分匹配最相关 skill"""
        task_lower = task.lower()
        matches: List[SkillMatch] = []

        for skill_name, keywords in self.KEYWORD_MAPPING.items():
            score = sum(
                1 for kw in keywords if kw.lower() in task_lower
            )
            if score > 0:
                confidence = min(score / len(keywords), 1.0)
                matches.append(SkillMatch(
                    skill_name=skill_name,
                    confidence=confidence,
                ))

        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches[: self.config.max_skills_per_task]

    # ── 公开接口 ──

    async def plan(self, request: AgentRequest, available_skills: List[Any], context: Dict[str, Any]) -> Plan:
        output = await self.plan_calls(request, available_skills, context)
        return self._build_plan_from_output(output, request, available_skills, context)

    async def plan_calls(self, request: AgentRequest, available_skills: List[Any], context: Dict[str, Any]) -> PlannerOutput:
        """规则规划核心：匹配 skill + 提取参数 → 输出 PlannerOutput"""
        skill_map = {s.name: s for s in available_skills}

        # 1) 确定候选 skills
        if request.skills:
            # 用户显式指定了 skills
            candidates = [
                SkillMatch(skill_name=name, confidence=1.0)
                for name in request.skills
                if name in skill_map
            ]
            if not candidates and available_skills:
                candidates = [SkillMatch(skill_name=available_skills[0].name, confidence=0.5)]
        else:
            # 从任务文本中匹配
            candidates = self._match_skill_by_keywords(request.task)
            if not candidates and available_skills:
                candidates = [SkillMatch(skill_name=available_skills[0].name, confidence=0.3)]

        # 2) 对每个候选 skill 提取参数并构建 SkillCall
        calls: List[SkillCall] = []
        reasoning_parts: List[str] = []

        for match in candidates:
            if match.skill_name not in skill_map:
                continue

            extracted = ParamExtractor.extract(request.task, match.skill_name)

            call = SkillCall(
                skill=match.skill_name,
                args=extracted,
                confidence=match.confidence,
            )
            calls.append(call)

            if extracted:
                reasoning_parts.append(
                    f"[{match.skill_name}] 提取参数: {list(extracted.keys())}"
                )
            else:
                reasoning_parts.append(f"[{match.skill_name}] 使用默认参数")

        return PlannerOutput(
            calls=calls,
            reasoning=f"规则匹配完成 ({len(calls)} 个 skill): {'; '.join(reasoning_parts)}",
        )


# ────────────────── LLM 规划器 ──────────────────


class LLMPlanner(BasePlanner):
    """基于大语言模型的智能规划器

    相比 RuleBasedPlanner 的优势:
      - 能理解复杂/模糊的任务描述
      - 能做多步推理判断该调哪些 skill
      - 能从隐式上下文中提取更精准的参数

    回退策略:
      - 无 LLM adapter → 回退到 RuleBasedPlanner
      - JSON 解析失败 → 回退到 RuleBasedPlanner
      - LLM 返回无效 skill 名 → 过滤后若空则回退
    """

    def __init__(self, config: Optional[PlannerConfig] = None):
        self.config = config or PlannerConfig()
        self._llm_adapter: Optional[Any] = None

    def set_llm_adapter(self, adapter: Any) -> None:
        """注入 LLM 调用适配器（需实现 .chat(messages) -> LLMResponse）"""
        self._llm_adapter = adapter

    async def plan(self, request: AgentRequest, available_skills: List[Any], context: Dict[str, Any]) -> Plan:
        output = await self.plan_calls(request, available_skills, context)
        rule_fallback = RuleBasedPlanner(self.config)
        return rule_fallback._build_plan_from_output(output, request, available_skills, context)

    async def plan_calls(self, request: AgentRequest, available_skills: List[Any], context: Dict[str, Any]) -> PlannerOutput:
        """LLM 规划核心：构造 prompt → 调用 LLM → 解析 SkillCall 列表"""

        # ── 无 adapter 时直接回退 ──
        if not self._llm_adapter:
            return await RuleBasedPlanner(self.config).plan_calls(request, available_skills, context)

        # ── 构造 Skill 描述（含参数 Schema）──
        skill_blocks = self._format_skill_descriptions(available_skills)

        prompt = f"""你是一个 Linux 应急响应系统的任务规划师。请分析用户的任务需求，选择最合适的 Skill 来完成。

## 可用 Skills

{skill_blocks}

## 用户任务
{request.task}

## 输出要求
请以 **纯 JSON** 返回（不要 markdown 代码块标记），格式如下：

```json
{{
  "calls": [
    {{
      "skill": "skill_名称",
      "args": {{ "参数名": "从任务中推断的值" }},
      "confidence": 0.95
    }}
  ],
  "reasoning": "简要说明为什么选择这些 skill 以及参数推断依据"
}}
```

## 规则
1. 只选择真正需要的 skill（通常 1~2 个），不要贪多
2. args 中只填写你能**明确推断**出来的参数，不确定的不填（让 skill 使用默认值）
3. confidence 反映你的确信程度 (0.0~1.0)
4. skill 名称必须来自上面的「可用 Skills」列表
5. 只返回 JSON，不要有其他文字
"""

        messages = [Message(role=ModelRole.USER, content=prompt)]

        try:
            response = await self._llm_adapter.chat(messages)
            raw_text = response.content.strip()

            # 清理可能的 markdown 包裹
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
                raw_text = re.sub(r"\n?```$", "", raw_text).strip()

            raw_data: Dict[str, Any] = json.loads(raw_text)

            # 兼容旧版 {"skills": [...]} 格式
            if "skills" in raw_data and "calls" not in raw_data:
                raw_data["calls"] = [
                    SkillCall(skill=str(name), args={}, confidence=0.8).model_dump()
                    for name in raw_data.get("skills", [])
                ]
                raw_data.pop("skills", None)

            # 校验为 PlannerOutput
            output = PlannerOutput.model_validate(raw_data)

            # 过滤无效 skill 名
            valid_names = {s.name for s in available_skills}
            before_count = len(output.calls)
            output.calls = [c for c in output.calls if c.skill in valid_names]
            after_count = len(output.calls)

            if after_count < before_count:
                output.reasoning += f" (过滤了 {before_count - after_count} 个无效 skill)"

            if not output.calls:
                output.reasoning += " (LLM 未返回有效 skill)"

            return output

        except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as parse_err:
            # JSON 解析或字段校验失败 → 回退到规则规划器
            fallback = RuleBasedPlanner(self.config)
            result = await fallback.plan_calls(request, available_skills, context)
            result.reasoning += f" (LLM 解析失败回退: {parse_err})"
            return result

        except Exception as e:
            # 其他异常（网络超时、API 错误等）→ 回退
            fallback = RuleBasedPlanner(self.config)
            result = await fallback.plan_calls(request, available_skills, context)
            result.reasoning += f" (LLM 异常回退: {type(e).__name__})"
            return result

    # ── Prompt 构建辅助 ──

    @staticmethod
    def _format_skill_descriptions(skills: List[Any]) -> str:
        """将 skills 格式化为 LLM 友好的文本（含参数 Schema）"""
        blocks: List[str] = []

        for s in skills:
            param_lines: List[str] = []

            if s.parameters:
                for p in s.parameters:
                    req_str = "必填" if p.required else f"可选(默认={p.default})"
                    param_lines.append(f"      - `{p.name}` ({p.type}): {p.description} [{req_str}]")

            param_section = ""
            if param_lines:
                param_section = "\n    参数:\n" + "\n".join(param_lines)

            blocks.append(f"- **{s.name}** [{s.category}]: {s.description}{param_section}")

        return "\n\n".join(blocks)


# ────────────────── 工厂函数 ──────────────────


def create_planner(config: Optional[PlannerConfig] = None) -> BasePlanner:
    """根据配置创建对应的 Planner 实例

    Args:
        config: Planner 配置，None 则使用默认值（RuleBasedPlanner）

    Returns:
        启用了 LLM 时返回 LLMPlanner，否则返回 RuleBasedPlanner
    """
    cfg = config or PlannerConfig()
    if cfg.enable_llm_planner:
        return LLMPlanner(cfg)
    return RuleBasedPlanner(cfg)
