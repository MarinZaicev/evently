import {
  CalendarDays,
  MapPin,
  Ticket,
  X,
} from 'lucide-react'

import type {
  ApiEvent,
} from '../lib/api'

type Props = {
  event: ApiEvent
  onClose: () => void
  onTicket: () => void
}

function formatDate(event: ApiEvent) {
  const occurrence =
    event.occurrences[0]

  if (!occurrence) {
    return '\u0412 \u043b\u044e\u0431\u043e\u0435 \u0432\u0440\u0435\u043c\u044f'
  }

  return new Intl.DateTimeFormat(
    'ru-RU',
    {
      day: 'numeric',
      month: 'long',
      hour: '2-digit',
      minute: '2-digit',
    },
  ).format(
    new Date(occurrence.startsAt),
  )
}

function formatPrice(event: ApiEvent) {
  if (event.isFree) {
    return '\u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e'
  }

  if (event.priceMin !== null) {
    return `\u043e\u0442 ${event.priceMin.toLocaleString(
      'ru-RU',
    )} \u20bd`
  }

  return '\u0426\u0435\u043d\u0430 \u0443\u0442\u043e\u0447\u043d\u044f\u0435\u0442\u0441\u044f'
}

export function EventDetailsSheet({
  event,
  onClose,
  onTicket,
}: Props) {
  const image =
    event.images[0]?.url

  const description =
    event.description ??
    event.shortDescription

  const hasLink =
    Boolean(
      event.ticketUrl ??
      event.sourceUrl,
    )

  return (
    <div
      className="details-backdrop"
      onClick={onClose}
    >
      <div
        className="details-sheet"
        onClick={(event) =>
          event.stopPropagation()
        }
      >
        <button
          type="button"
          className="details-close"
          onClick={onClose}
        >
          <X size={22} />
        </button>

        {image && (
          <img
            className="details-image"
            src={image}
            alt=""
          />
        )}

        <div className="details-body">
          <div className="details-categories">
            {event.categories
              .slice(0, 3)
              .map((category) => (
                <span key={category.id}>
                  {category.icon}{' '}
                  {category.name}
                </span>
              ))}
          </div>

          <h2>{event.title}</h2>

          <div className="details-meta">
            <div>
              <CalendarDays size={18} />
              <span>
                {formatDate(event)}
              </span>
            </div>

            {event.venue && (
              <div>
                <MapPin size={18} />
                <span>
                  {event.venue.name}
                </span>
              </div>
            )}

            {event.venue?.address && (
              <div className="details-address">
                {event.venue.address}
              </div>
            )}
          </div>

          {description && (
            <p className="details-description">
              {description}
            </p>
          )}

          <div className="details-footer">
            <strong className="details-price">
              {formatPrice(event)}
            </strong>

            {hasLink && (
              <button
                type="button"
                className="details-ticket-button"
                onClick={onTicket}
              >
                <Ticket size={19} />

                {event.ticketUrl
                  ? '\u041a\u0443\u043f\u0438\u0442\u044c \u0431\u0438\u043b\u0435\u0442'
                  : '\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
