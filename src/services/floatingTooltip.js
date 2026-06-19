const registrations = new Map()

let listenersAttached = false

function hideRegistration(registration) {
  if (registration.isVisible()) registration.hide()
}

function handleDocumentMouseMove(event) {
  registrations.forEach((registration) => {
    if (!registration.isVisible()) return

    const container = registration.getContainer()
    if (container && !container.contains(event.target)) registration.hide()
  })
}

function hideAllTooltips() {
  registrations.forEach(hideRegistration)
}

function attachListeners() {
  if (listenersAttached || typeof document === 'undefined') return
  document.addEventListener('mousemove', handleDocumentMouseMove, true)
  window.addEventListener('blur', hideAllTooltips)
  listenersAttached = true
}

function detachListenersIfIdle() {
  if (!listenersAttached || registrations.size) return
  document.removeEventListener('mousemove', handleDocumentMouseMove, true)
  window.removeEventListener('blur', hideAllTooltips)
  listenersAttached = false
}

export function registerFloatingTooltip(owner, registration) {
  registrations.set(owner, registration)
  attachListeners()

  return () => {
    registrations.delete(owner)
    detachListenersIfIdle()
  }
}

export function activateFloatingTooltip(owner) {
  registrations.forEach((registration, registeredOwner) => {
    if (registeredOwner !== owner) hideRegistration(registration)
  })
}
