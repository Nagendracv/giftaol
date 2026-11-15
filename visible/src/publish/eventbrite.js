// Eventbrite, through its official API (https://www.eventbrite.com/platform/api).
// Visible only ever creates DRAFT events. A volunteer opens the draft in Eventbrite and presses Publish there.
import { tzForProvince, zonedToUtc } from './platforms.js';

const API = 'https://www.eventbriteapi.com/v3';

async function call(fetchImpl, token, path, { method = 'GET', body } = {}) {
  const res = await fetchImpl(API + path, {
    method,
    headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`Eventbrite said: ${json.error_description || json.error || res.status}`);
  return json;
}

export async function organizationId(token, fetchImpl = fetch) {
  if (process.env.EVENTBRITE_ORG_ID) return process.env.EVENTBRITE_ORG_ID;
  const me = await call(fetchImpl, token, '/users/me/organizations/');
  const id = me.organizations?.[0]?.id;
  if (!id) throw new Error('This Eventbrite account has no organization.');
  return id;
}

const htmlPara = (s) => s.split('\n\n').map((p) => `<p>${p.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]).replace(/\n/g, '<br>')}</p>`).join('');

// pkg: the Eventbrite package from eventPackages(); event: the form values.
export async function createDraftEvent({ token, pkg, event, fetchImpl = fetch }) {
  const org = await organizationId(token, fetchImpl);
  const timezone = tzForProvince(event.province);
  let venueId;
  if (!event.online && event.address) {
    const v = await call(fetchImpl, token, `/organizations/${org}/venues/`, {
      method: 'POST',
      body: { venue: { name: event.venue || `Art of Living ${event.city}`, address: { address_1: event.address, city: event.city, region: event.province, country: 'CA' } } },
    });
    venueId = v.id;
  }
  const created = await call(fetchImpl, token, `/organizations/${org}/events/`, {
    method: 'POST',
    body: {
      event: {
        name: { html: pkg.title },
        summary: pkg.summary,
        description: { html: htmlPara(pkg.body) },
        start: { timezone, utc: zonedToUtc(event.start, timezone) },
        end: { timezone, utc: zonedToUtc(event.end || event.start, timezone) },
        currency: 'CAD',
        online_event: !!event.online,
        ...(venueId ? { venue_id: venueId } : {}),
        capacity: Number(event.capacity) || 30,
      },
    },
  });
  await call(fetchImpl, token, `/events/${created.id}/ticket_classes/`, {
    method: 'POST',
    body: { ticket_class: { name: 'Free registration', free: true, quantity_total: Number(event.capacity) || 30 } },
  });
  return { id: created.id, url: created.url, status: created.status ?? 'draft', manageUrl: `https://www.eventbrite.ca/myevent?eid=${created.id}` };
}

// Registrations for a posted event. Eventbrite's API does not share page views; those stay in its dashboard.
export async function eventStats({ token, eventId, fetchImpl = fetch }) {
  const [ev, tc] = await Promise.all([
    call(fetchImpl, token, `/events/${eventId}/`),
    call(fetchImpl, token, `/events/${eventId}/ticket_classes/`),
  ]);
  const classes = tc.ticket_classes ?? [];
  return {
    status: ev.status,
    url: ev.url,
    registered: classes.reduce((n, c) => n + (c.quantity_sold ?? 0), 0),
    capacity: classes.reduce((n, c) => n + (c.quantity_total ?? 0), 0) || ev.capacity || null,
    checkedAt: new Date().toISOString(),
  };
}
