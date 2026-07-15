export function defaultRange() {
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), 1);
  const fmt = (d) => d.toISOString().slice(0, 10);
  return { start: fmt(start), end: fmt(today) };
}
