# mypy: disable-error-code="override"
from collections.abc import Mapping
from typing import Any, Optional, Union, cast

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.chat_models.base import BaseChatModel
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .util import YException
from .YandexGPT import YandexLLM


class ChatYandexGPT(YandexLLM, BaseChatModel):  # type: ignore[misc]
    """
    Custom LLM for langchain.
    =========================

    Proprietary LLM shell for YandexGPT, as it is not supported in LangChain.
    https://python.langchain.com/docs/modules/model_io/llms/custom_llm/

    Methods:
    --------
    \n\tconv_message
    \n\t__call__
    \n\t_generate

    """

    @staticmethod
    def conv_message(msg: BaseMessage) -> dict[str, str]:
        msg_content = cast(str, msg.content)
        if isinstance(msg, HumanMessage):
            return YandexLLM.UserMessage(msg_content)
        if isinstance(msg, AIMessage):
            return YandexLLM.AssistantMessage(msg_content)
        if isinstance(msg, SystemMessage):
            return YandexLLM.SystemMessage(msg_content)
        raise YException('Unknown message type')

    def __call__(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AIMessage:
        return self._generate(messages, **kwargs)

    def _generate(
        self,
        prompts: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AIMessage:
        msg: list[Mapping[Any, Any]] = [self.conv_message(x) for x in prompts]
        res = cast(Union[str, list[Union[str, dict[Any, Any]]]], super()._generate_messages(msg, **kwargs))
        return AIMessage(content=res)
