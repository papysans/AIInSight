from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.config import settings
from app.services.user_settings import get_effective_llm_keys, get_agent_llm_overrides, get_agent_api_config
from typing import Dict, List, Optional

class KeyManager:
    def __init__(self, keys, provider_name="Unknown"):
        self.keys = [k for k in (keys or []) if k]
        self.provider_name = provider_name
        self._idx = 0

    def get_next_key(self):
        if not self.keys:
            raise ValueError(f"No API keys configured for {self.provider_name}.")
        k = self.keys[self._idx % len(self.keys)]
        self._idx = (self._idx + 1) % len(self.keys)
        return k

_key_managers: Dict[str, KeyManager] = {}


def _get_manager(provider_key: str, keys: List[str], provider_name: str) -> KeyManager:
    """
    Keep per-provider rotation state while allowing keys to change at runtime.
    If keys changed, replace the manager.
    """
    pk = (provider_key or "").strip().lower()
    existing = _key_managers.get(pk)
    normalized = [k for k in (keys or []) if k]
    if not existing or existing.keys != normalized:
        existing = KeyManager(normalized, provider_name)
        _key_managers[pk] = existing
    return existing

def get_llm(provider: str, model_name: str, api_key: Optional[str] = None):
    """
    Factory function to get an LLM instance based on provider and model.
    If api_key is provided, use it directly; otherwise use key rotation.
    """
    if provider == "google" or provider == "gemini":
        if api_key:
            current_key = api_key
            print(f"🔑 Using Agent-specific Gemini Key: ...{current_key[-6:]}")
        else:
            keys = get_effective_llm_keys(provider_key="gemini", env_keys=settings.GEMINI_API_KEYS)
            current_key = _get_manager("gemini", keys, "Gemini").get_next_key()
            print(f"🔑 Using Gemini Key: ...{current_key[-6:]}")
        
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.7,
            google_api_key=current_key,
            convert_system_message_to_human=True
        )
        
    elif provider == "moonshot":
        if api_key:
            current_key = api_key
            print(f"🔑 Using Agent-specific Moonshot Key: ...{current_key[-6:]}")
        else:
            keys = get_effective_llm_keys(provider_key="kimi", env_keys=settings.MOONSHOT_API_KEYS)
            current_key = _get_manager("moonshot", keys, "Moonshot").get_next_key()
            print(f"🔑 Using Moonshot Key: ...{current_key[-6:]}")
        return ChatOpenAI(
            model=model_name,
            temperature=0.7,
            api_key=current_key,
            base_url=settings.MOONSHOT_BASE_URL
        )

    elif provider == "openai":
        if api_key:
            current_key = api_key
            print(f"🔑 Using Agent-specific OpenAI Key: ...{current_key[-6:]}")
        else:
            keys = get_effective_llm_keys(provider_key="openai", env_keys=[settings.OPENAI_API_KEY])
            current_key = keys[0] if keys else settings.OPENAI_API_KEY
            print(f"🔑 Using OpenAI Key: ...{current_key[-6:]}")
        return ChatOpenAI(
            model=model_name,
            temperature=0.7,
            api_key=current_key
        )

    elif provider == "deepseek":
        if api_key:
            current_key = api_key
            print(f"🔑 Using Agent-specific DeepSeek Key: ...{current_key[-6:]}")
        else:
            keys = get_effective_llm_keys(provider_key="deepseek", env_keys=settings.DEEPSEEK_API_KEYS)
            current_key = _get_manager("deepseek", keys, "DeepSeek").get_next_key()
            print(f"🔑 Using DeepSeek Key: ...{current_key[-6:]}")
        return ChatOpenAI(
            model=model_name,
            temperature=0.7,
            api_key=current_key,
            base_url=settings.DEEPSEEK_BASE_URL
        )

    elif provider == "doubao":
        if api_key:
            current_key = api_key
            print(f"🔑 Using Agent-specific Doubao Key: ...{current_key[-6:]}")
        else:
            keys = get_effective_llm_keys(provider_key="doubao", env_keys=settings.DOUBAO_API_KEYS)
            current_key = _get_manager("doubao", keys, "Doubao").get_next_key()
            print(f"🔑 Using Doubao Key: ...{current_key[-6:]}")
        return ChatOpenAI(
            model=model_name,
            temperature=0.7,
            api_key=current_key,
            base_url=settings.DOUBAO_BASE_URL
        )

    elif provider == "zhipu":
        if api_key:
            current_key = api_key
            print(f"🔑 Using Agent-specific Zhipu Key: ...{current_key[-6:]}")
        else:
            keys = get_effective_llm_keys(provider_key="zhipu", env_keys=settings.ZHIPU_API_KEYS)
            current_key = _get_manager("zhipu", keys, "Zhipu").get_next_key()
            print(f"🔑 Using Zhipu Key: ...{current_key[-6:]}")
        return ChatOpenAI(
            model=model_name,
            temperature=0.7,
            api_key=current_key,
            base_url=settings.ZHIPU_BASE_URL
        )
    
    else:
        raise ValueError(f"Unsupported LLM Provider: {provider}")

class ResilientChatModel:
    """
    A wrapper around multiple LLM providers that implements fallback logic.
    If one provider fails, it automatically tries the next one in the list.
    """
    def __init__(self, configs, agent_name: Optional[str] = None):
        self.configs = configs if isinstance(configs, list) else [configs]
        self.agent_name = agent_name

    async def ainvoke(self, messages, **kwargs):
        """
        Invoke LLM with automatic fallback to alternative providers.
        """
        # Check if agent has specific API configuration
        agent_config = None
        if self.agent_name:
            agent_config = get_agent_api_config(self.agent_name)
        
        errors = []
        for idx, config in enumerate(self.configs):
            provider = config["provider"]
            model = config["model"]
            
            # Use agent-specific API key if available
            api_key = None
            if agent_config and agent_config["provider"].lower() == _PROVIDERKEY_TO_PROVIDER.get(provider.lower(), provider).lower():
                api_key = agent_config["key"]
                if agent_config["model"]:
                    model = agent_config["model"]
                print(f"🎯 [Agent Override] Using {self.agent_name}'s API: {provider} ({model})")
            
            try:
                llm = get_llm(provider, model, api_key=api_key)
                if idx == 0:
                    print(f"🎯 [LLM] Using {provider} ({model})")
                else:
                    print(f"🔄 [LLM Fallback] Trying {provider} ({model})...")
                
                result = await llm.ainvoke(messages, **kwargs)
                
                # Success - log and return
                if idx > 0:
                    print(f"✅ [LLM Fallback] Success with {provider}")
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ [LLM Error] {provider} failed: {error_msg[:100]}")
                errors.append(f"{provider}: {error_msg}")
                
                # If this is the last provider, raise the error
                if idx == len(self.configs) - 1:
                    break
                    
                # Otherwise, continue to next provider
                print(f"🔁 [LLM] Switching to next provider...")
                continue
        
        # All providers failed
        raise Exception(f"❌ All {len(self.configs)} LLM providers failed:\n" + "\n".join(errors))


_PROVIDERKEY_TO_PROVIDER = {
    # frontend providerKey -> backend provider in config/get_llm
    "deepseek": "deepseek",
    "gemini": "gemini",
    "doubao": "doubao",
    "zhipu": "zhipu",
    "openai": "openai",
    # Kimi in frontend maps to moonshot in backend
    "kimi": "moonshot",
}


def _apply_agent_override(agent_name: str, configs: List[dict]) -> List[dict]:
    """
    Reorder agent provider list to prefer user-selected provider (if any).
    New logic: If agent has a specific API config, use that exclusively.
    """
    if not configs:
        return configs
    
    # Check if agent has a specific API configuration
    agent_config = get_agent_api_config(agent_name)
    if agent_config:
        # Agent has specific API config - use it exclusively
        provider = agent_config["provider"]
        model = agent_config["model"]
        
        # Map frontend provider key to backend provider
        backend_provider = _PROVIDERKEY_TO_PROVIDER.get(provider.lower(), provider)
        
        print(f"🎯 [Agent Override] {agent_name} -> {backend_provider} ({model or 'default'})")
        
        # Return single config with agent's specific settings
        return [{
            "provider": backend_provider,
            "model": model or configs[0].get("model", "")  # Use agent's model or fallback to default
        }]
    
    # No specific override - use old logic for backward compatibility
    overrides = get_agent_llm_overrides()
    override_data = overrides.get(agent_name)
    if not override_data:
        return configs
    
    selected_pk = override_data.get("provider", "").strip().lower()
    if not selected_pk:
        return configs
    
    selected_provider = _PROVIDERKEY_TO_PROVIDER.get(selected_pk)
    if not selected_provider:
        return configs

    preferred: List[dict] = []
    rest: List[dict] = []
    for c in configs:
        if (c.get("provider") or "").strip().lower() == selected_provider:
            preferred.append(c)
        else:
            rest.append(c)
    return preferred + rest


def get_agent_llm(agent_name: str):
    """
    Get the configured LLM for a specific agent.
    Returns a ResilientChatModel that handles automatic fallback.
    """
    config = settings.AGENT_CONFIG.get(agent_name)
    if not config:
        # Fallback to default if agent not found
        print(f"⚠️ [Config] Agent '{agent_name}' not configured, using default")
        return get_llm("deepseek", settings.DEEPSEEK_MODEL)

    # Apply user override to reorder provider preference
    cfg_list = config if isinstance(config, list) else [config]
    cfg_list = _apply_agent_override(agent_name, cfg_list)
    return ResilientChatModel(cfg_list, agent_name=agent_name)
