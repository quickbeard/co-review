import { Badge } from "@/components/ui/badge";
import type { LLMProviderType } from "@/lib/api/llm-provider-types";

const providerColors: Record<LLMProviderType, string> = {
  openai: "bg-emerald-600 text-white",
  anthropic: "bg-orange-600 text-white",
  cohere: "bg-purple-600 text-white",
  replicate: "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900",
  groq: "bg-blue-600 text-white",
  xai: "bg-gray-800 text-white dark:bg-gray-200 dark:text-gray-900",
  huggingface: "bg-yellow-500 text-black",
  ollama: "bg-slate-700 text-white dark:bg-slate-300 dark:text-slate-900",
  vertexai: "bg-blue-500 text-white",
  google_ai_studio: "bg-blue-400 text-white",
  deepseek: "bg-indigo-600 text-white",
  deepinfra: "bg-pink-600 text-white",
  azure_openai: "bg-sky-600 text-white",
  azure_ad: "bg-sky-700 text-white",
  openrouter: "bg-violet-600 text-white",
  aws_bedrock: "bg-amber-600 text-white",
  litellm: "bg-teal-600 text-white",
};

const providerLabels: Record<LLMProviderType, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  cohere: "Cohere",
  replicate: "Replicate",
  groq: "Groq",
  xai: "xAI",
  huggingface: "Hugging Face",
  ollama: "Ollama",
  vertexai: "Vertex AI",
  google_ai_studio: "Google AI Studio",
  deepseek: "DeepSeek",
  deepinfra: "DeepInfra",
  azure_openai: "Azure OpenAI",
  azure_ad: "Azure AD",
  openrouter: "OpenRouter",
  aws_bedrock: "AWS Bedrock",
  litellm: "LiteLLM",
};

interface LLMProviderTypeBadgeProps {
  type: LLMProviderType;
}

export function LLMProviderTypeBadge({ type }: LLMProviderTypeBadgeProps) {
  return (
    <Badge variant="outline" className={providerColors[type]}>
      {providerLabels[type]}
    </Badge>
  );
}
