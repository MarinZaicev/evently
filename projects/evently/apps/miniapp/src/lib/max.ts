type MaxWebApp = {
  initData?: string
}

declare global {
  interface Window {
    WebApp?: MaxWebApp
  }
}

function getInitDataFromHash() {
  if (
    typeof window ===
      'undefined'
  ) {
    return ''
  }

  const hash =
    window.location.hash

  if (!hash) {
    return ''
  }

  const params =
    new URLSearchParams(
      hash.startsWith('#')
        ? hash.slice(1)
        : hash,
    )

  return (
    params.get('WebAppData') ??
    ''
  )
}

export function getMaxInitData() {
  if (
    typeof window ===
      'undefined'
  ) {
    return ''
  }

  const bridgeInitData =
    window.WebApp?.initData

  if (bridgeInitData) {
    return bridgeInitData
  }

  return getInitDataFromHash()
}
