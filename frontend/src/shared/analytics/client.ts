type AnalyticsEvent = { event_name: string; timestamp: string; props: Record<string, unknown> };

const queue: AnalyticsEvent[] = [];

export function track(event_name: string, props: Record<string, unknown> = {}) {
  queue.push({ event_name, timestamp: new Date().toISOString(), props });
  if (queue.length >= 20) void flush();
}

export async function flush() {
  if (!queue.length) return;
  const events = queue.splice(0, queue.length);
  try {
    await fetch("/api/v1/events", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
      keepalive: true,
    });
  } catch {
    // Analytics is best-effort and must not interrupt product flows.
  }
}

window.addEventListener("pagehide", () => {
  if (!queue.length) return;
  navigator.sendBeacon("/api/v1/events", JSON.stringify({ events: queue.splice(0, queue.length) }));
});
