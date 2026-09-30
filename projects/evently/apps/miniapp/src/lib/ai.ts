import {
  getClientId,
} from './interactions'

import {
  getMaxInitData,
} from './max'

export type AiChatMessage = {
  role: 'user' | 'assistant'
  content: string
  eventIds?: string[]
}

export type AiEventSuggestion = {
  id: string
  title: string
  imageUrl: string | null
  venue: string | null
  address: string | null
  price: string
  startsAt: string | null
  url: string | null
}

export type AiChatResponse = {
  answer: string
  events: AiEventSuggestion[]
}

export async function sendAiMessage(
  message: string,
  history: AiChatMessage[],
): Promise<AiChatResponse> {
  const maxInitData =
    getMaxInitData()

  const headers:
    Record<string, string> = {
      'Content-Type':
        'application/json',

      'x-evently-client-id':
        getClientId(),
    }

  if (maxInitData) {
    headers['x-max-init-data'] =
      maxInitData
  }

  const response = await fetch(
    '/api/ai/chat',
    {
      method: 'POST',
      headers,

      body: JSON.stringify({
        message,
        history:
          history.slice(-10),

        city: (() => {
          try {
            return (
              localStorage.getItem(
                'evently-city',
              ) ?? 'msk'
            )
          } catch {
            return 'msk'
          }
        })(),
      }),
    },
  )

  if (!response.ok) {
    const body =
      await response
        .text()
        .catch(() => '')

    throw new Error(
      `AI request failed: ${response.status} ${body}`,
    )
  }

  return response.json()
}
