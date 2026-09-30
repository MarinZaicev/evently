import {
  useMemo,
  useState,
} from 'react'

import {
  ArrowRight,
  Check,
  Sparkles,
} from 'lucide-react'

import type {
  ApiCategory,
} from '../lib/profile'

type Props = {
  categories: ApiCategory[]
  onComplete: (
    selected: string[],
  ) => Promise<void>
}

export function Onboarding({
  categories,
  onComplete,
}: Props) {
  const [selected, setSelected] =
    useState<string[]>([])

  const [saving, setSaving] =
    useState(false)

  const selectedSet =
    useMemo(
      () => new Set(selected),
      [selected],
    )

  function toggleCategory(
    slug: string,
  ) {
    setSelected((current) => {
      if (current.includes(slug)) {
        return current.filter(
          (item) => item !== slug,
        )
      }

      return [...current, slug]
    })
  }

  async function submit() {
    if (
      selected.length < 3 ||
      saving
    ) {
      return
    }

    setSaving(true)

    try {
      await onComplete(selected)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="onboarding">
      <div className="onboarding-glow onboarding-glow-one" />
      <div className="onboarding-glow onboarding-glow-two" />

      <div className="onboarding-content">
        <div className="onboarding-brand">
          <Sparkles size={18} />
          <span>EVENTLY</span>
        </div>

        <div className="onboarding-heading">
          <h1>
            Что тебе
            <br />
            нравится?
          </h1>

          <p>
            Выбери хотя бы 3 темы.
            Мы соберём первую ленту,
            а дальше она сама
            подстроится под тебя.
          </p>
        </div>

        <div className="interest-grid">
          {categories.map(
            (category) => {
              const active =
                selectedSet.has(
                  category.slug,
                )

              return (
                <button
                  key={category.id}
                  type="button"
                  className={
                    active
                      ? 'interest-card active'
                      : 'interest-card'
                  }
                  onClick={() =>
                    toggleCategory(
                      category.slug,
                    )
                  }
                >
                  <span className="interest-icon">
                    {category.icon ?? '✦'}
                  </span>

                  <span className="interest-name">
                    {category.name}
                  </span>

                  <span className="interest-check">
                    {active && (
                      <Check size={14} />
                    )}
                  </span>
                </button>
              )
            },
          )}
        </div>

        <div className="onboarding-footer">
          <div className="selection-counter">
            {selected.length < 3
              ? `Выбери ещё ${
                  3 - selected.length
                }`
              : `Выбрано: ${selected.length}`}
          </div>

          <button
            className="onboarding-submit"
            type="button"
            disabled={
              selected.length < 3 ||
              saving
            }
            onClick={() =>
              void submit()
            }
          >
            <span>
              {saving
                ? 'Сохраняем...'
                : 'Собрать мою ленту'}
            </span>

            {!saving && (
              <ArrowRight size={20} />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
