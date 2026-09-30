export function getInteractionWeight(
  interaction: {
    type: string
    durationMs: number | null
  },
) {
  switch (interaction.type) {
    case 'FAVORITE':
      return 5

    case 'UNFAVORITE':
      return -5

    case 'OPEN':
      return 2

    case 'SHARE':
      return 6

    case 'TICKET_CLICK':
      return 8

    case 'HIDE':
      return -8

    case 'DWELL': {
      const duration =
        interaction.durationMs ?? 0

      if (duration >= 15_000) {
        return 3
      }

      if (duration >= 5_000) {
        return 1.5
      }

      if (duration < 1_500) {
        return -0.5
      }

      return 0
    }

    default:
      return 0
  }
}
