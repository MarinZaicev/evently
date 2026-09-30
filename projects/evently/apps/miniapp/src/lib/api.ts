import type {
  ApiEvent,
  ApiEventsResponse,
} from '@evently/shared'

import {
  getClientId,
} from './interactions'

export async function getEvents(
  limit = 20,
  category?: string,
  latitude?: number,
  longitude?: number,
  city?: string,
): Promise<ApiEventsResponse> {
  const params =
    new URLSearchParams()

  params.set(
    'limit',
    String(limit),
  )

  if (category) {
    params.set(
      'category',
      category,
    )
  }

  let effectiveCity =
    city

  if (!effectiveCity) {
    try {
      effectiveCity =
        localStorage.getItem(
          'evently-city',
        ) ?? 'msk'
    } catch {
      effectiveCity = 'msk'
    }
  }

  params.set(
    'city',
    effectiveCity,
  )

  if (
    latitude !== undefined &&
    longitude !== undefined
  ) {
    params.set(
      'latitude',
      String(latitude),
    )

    params.set(
      'longitude',
      String(longitude),
    )
  }

  const response = await fetch(
    `/api/feed/?${params.toString()}`,
    {
      headers: {
        'x-evently-client-id':
          getClientId(),
      },
    },
  )

  if (!response.ok) {
    throw new Error(
      `Failed to load feed: ${response.status}`,
    )
  }

  return response.json()
}

export type {
  ApiEvent,
}
