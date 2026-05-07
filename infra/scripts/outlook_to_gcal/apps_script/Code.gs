// Life OS - Outlook to Google Calendar (Apps Script Web App receiver).
// PowerShell POSTs events.json; this upserts them to the deployer's
// Google Calendar. Idempotent via (subject + start +/- 60s) match because
// CalendarApp does not expose extendedProperties for direct lookup.
//
// Deploy as Web App: execute as Me, access "Anyone".
// Replace SHARED_SECRET below with a 32+ char random string and put the
// same value in .env GCAL_APPSCRIPT_TOKEN.

const SHARED_SECRET = 'CHANGE_ME_TO_A_LONG_RANDOM_STRING';
const CAL_ID = 'primary';


function doPost(e) {
  const auth = (e && e.parameter && e.parameter.token) || '';
  if (auth !== SHARED_SECRET) {
    return _json({ ok: false, error: 'unauthorized' });
  }

  let payload;
  try {
    payload = JSON.parse(e.postData.contents);
  } catch (err) {
    return _json({ ok: false, error: 'invalid_json: ' + err.message });
  }

  const cal = (CAL_ID === 'primary')
    ? CalendarApp.getDefaultCalendar()
    : CalendarApp.getCalendarById(CAL_ID);
  if (!cal) {
    return _json({ ok: false, error: 'calendar_not_found: ' + CAL_ID });
  }

  const events = (payload && payload.events) || [];
  const counters = { newCount: 0, updCount: 0, skipCount: 0, errCount: 0 };
  const errors = [];

  for (let i = 0; i < events.length; i++) {
    try {
      _upsertOne(cal, events[i], counters);
    } catch (err) {
      counters.errCount++;
      errors.push({ subject: events[i].subject || '?', error: String(err) });
    }
  }

  return _json({
    ok: true,
    received: events.length,
    counters: counters,
    errors: errors
  });
}


function doGet(e) {
  return _json({
    ok: true,
    message: 'POST events with ?token=SHARED_SECRET to upsert',
    calendar: CAL_ID
  });
}


function _upsertOne(cal, ev, counters) {
  const subject = ev.subject || '(no title)';
  const start = new Date(ev.start);
  const end = new Date(ev.end);

  const dayStart = new Date(start.getFullYear(), start.getMonth(), start.getDate(), 0, 0, 0);
  const dayEnd = new Date(start.getFullYear(), start.getMonth(), start.getDate(), 23, 59, 59);
  const candidates = cal.getEvents(dayStart, dayEnd);

  let existing = null;
  for (let i = 0; i < candidates.length; i++) {
    const c = candidates[i];
    if (c.getTitle() !== subject) continue;
    if (Math.abs(c.getStartTime().getTime() - start.getTime()) > 60000) continue;
    existing = c;
    break;
  }

  if (existing) {
    let changed = false;
    const desc = ev.body || '';
    const loc = ev.location || '';
    if (existing.getDescription() !== desc) { existing.setDescription(desc); changed = true; }
    if (existing.getLocation() !== loc) { existing.setLocation(loc); changed = true; }
    if (existing.getEndTime().getTime() !== end.getTime()) {
      existing.setTime(start, end);
      changed = true;
    }
    if (changed) counters.updCount++; else counters.skipCount++;
  } else {
    if (ev.is_all_day) {
      cal.createAllDayEvent(subject, start);
    } else {
      cal.createEvent(subject, start, end, {
        description: ev.body || '',
        location: ev.location || ''
      });
    }
    counters.newCount++;
  }
}


function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj, null, 2))
    .setMimeType(ContentService.MimeType.JSON);
}
