import {
  CalendarDays,
  Heart,
  MapPin,
  MessageCircle,
  Share2,
  Ticket,
} from 'lucide-react'
import { useMemo, useState } from 'react'

import type {
  ApiEvent,
} from '../lib/api'

import {
  useEventView,
} from '../hooks/useEventView'

type Props = {
  event: ApiEvent
  position: number

  liked: boolean
  commentsCount: number

  onLike: () => void
  onComments: () => void
  onShare: () => void
  onDetails: () => void
}

function formatDate(
  event: ApiEvent,
) {
  const occurrence =
    event.occurrences[0]

  if (!occurrence) {
    return 'В любое время'
  }

  return new Intl.DateTimeFormat(
    'ru-RU',
    {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    },
  ).format(
    new Date(
      occurrence.startsAt,
    ),
  )
}

function formatPrice(
  event: ApiEvent,
) {
  if (event.isFree) {
    return 'Бесплатно'
  }

  if (event.priceMin !== null) {
    return `от ${event.priceMin.toLocaleString(
      'ru-RU',
    )} ?`
  }

  return 'Цена уточняется'
}

function getCategoryEmoji(
  event: ApiEvent,
) {
  const slug =
    event.categories[0]?.slug

  switch (slug) {
    case 'concert':
      return '??'
    case 'theatre':
      return '??'
    case 'cinema':
      return '??'
    case 'sport':
      return '??'
    case 'tour':
      return '???'
    case 'exhibition':
      return '??'
    case 'party':
      return '??'
    case 'standup':
      return '??'
    case 'games':
      return '??'
    case 'food':
      return '??'
    case 'family':
      return '????????'
    case 'education':
      return '??'
    default:
      return '?'
  }
}

function getFallbackLabel(
  event: ApiEvent,
) {
  return (
    event.categories[0]?.name ??
    'Событие'
  )
}

export function EventSlide({
  event,
  position,
  liked,
  commentsCount,
  onLike,
  onComments,
  onShare,
  onDetails,
}: Props) {
  const slideRef =
    useEventView(
      event.id,
      position,
    )

  const [imageFailed, setImageFailed] =
    useState(false)

  const image =
    event.images[0]?.url ?? null

  const showImage =
    Boolean(image) && !imageFailed

  const fallbackEmoji =
    useMemo(
      () => getCategoryEmoji(event),
      [event],
    )

  const fallbackLabel =
    useMemo(
      () => getFallbackLabel(event),
      [event],
    )

  return (
    <section
      ref={slideRef}
      className="event-slide"
    >
      <div className="slide-media">
        {showImage ? (
          <>
            <img
              className="slide-image-bg"
              src={image ?? undefined}
              alt=""
              aria-hidden="true"
              loading="lazy"
            />

            <img
              className="slide-image"
              src={image ?? undefined}
              alt={event.title}
              loading="lazy"
              onError={() =>
                setImageFailed(true)
              }
            />
          </>
        ) : (
          <div className="slide-image-fallback">
            <div className="slide-image-fallback-emoji">
              {fallbackEmoji}
            </div>

            <div className="slide-image-fallback-text">
              {fallbackLabel}
            </div>
          </div>
        )}

        <div className="slide-overlay" />
        <div className="slide-gradient" />
      </div>

      <div className="event-info">
        <div className="category-list">
          {event.categories
            .slice(0, 2)
            .map((category) => (
              <span
                key={category.id}
                className="category-pill"
              >
                {category.icon}{' '}
                {category.name}
              </span>
            ))}
        </div>

        <h1 className="event-name">
          {event.title}
        </h1>

        <div className="event-details">
          <div>
            <CalendarDays size={17} />

            <span>
              {formatDate(event)}
            </span>
          </div>

          {event.venue && (
            <div>
              <MapPin size={17} />

              <span>
                {event.venue.name}
              </span>
            </div>
          )}
        </div>

        {event.shortDescription && (
          <p className="event-description">
            {event.shortDescription}
          </p>
        )}

        <div className="bottom-actions">
          <div className="price">
            {formatPrice(event)}
          </div>

          <button
            type="button"
            className="ticket-button"
            onClick={onDetails}
          >
            <Ticket size={19} />
            Подробнее
          </button>
        </div>
      </div>

      <aside className="social-actions">
        <button
          type="button"
          className={
            liked
              ? 'social-button liked'
              : 'social-button'
          }
          onClick={onLike}
        >
          <span className="social-icon">
            <Heart
              size={29}
              fill={
                liked
                  ? 'currentColor'
                  : 'none'
              }
            />
          </span>

          <small>
            {liked ? 1 : 0}
          </small>
        </button>

        <button
          type="button"
          className="social-button"
          onClick={onComments}
        >
          <span className="social-icon">
            <MessageCircle
              size={29}
            />
          </span>

          <small>
            {commentsCount}
          </small>
        </button>

        <button
          type="button"
          className="social-button"
          onClick={onShare}
        >
          <span className="social-icon">
            <Share2 size={29} />
          </span>

          <small>
            Поделиться
          </small>
        </button>
      </aside>
    </section>
  )
}