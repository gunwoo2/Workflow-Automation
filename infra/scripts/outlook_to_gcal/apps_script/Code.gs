// Life OS — Outlook → Google Calendar (Apps Script Web App receiver)
//
// PowerShell이 events.json을 POST하면 본인 Google Calendar에 멱등 upsert.
// 배포 절차는 이 디렉터리 README.md 참조.
//
// 보안: SHARED_SECRET이 1차 방어선. URL이 길어서 추측은 어렵지만
// 노출 시 누구나 본인 캘린더에 쓸 수 있음 → secret + URL 둘 다 비밀 유지.

// ⚠️  배포 전 다음 두 값을 본인 것으로 교체:
const SHARED_SECRET = 'CHANGE_ME_TO_A_LONG_RANDOM_STRING';  // 32자 이상 랜덤 문자열 권장
const CAL_ID        = 'primary';                             // 또는 user@gmail.com / 캘린더 ID


// ---------- Entry points ----------

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
  const counters = { new: 0, upd: 0, skip: 0, err: 0 };
  const errors = [];

  for (let i = 0; i < events.length; i++) {
    try {
      _upsertOne(cal, events[i], counters);
    } catch (err) {
      counters.err++;
      errors.push({ subject: events[i].subject || '?', error: String(err) });
    }
  }

  return _json({
    ok: true,
    received: events.length,
    counters: counters,
    errors: errors,
  });
}

function doGet(e) {
  // Health check / 배포 검증용. POST 안 받음.
  return _json({
    ok: true,
    message: 'POST events.json with ?token=<SHARED_SECRET> to upsert.',
    calendar: CAL_ID,
  });
}


// ---------- Core ----------

function _upsertOne(cal, ev, counters) {
  const subject = ev.subject || '(no title)';
  const start = new Date(ev.start);
  const end = new Date(ev.end);

  // Apps Script CalendarApp은 extendedProperties 직접 노출이 약함 →
  // (subject + start ±60초) 매칭으로 idempotent. 같은 분에 같은 제목
  // 회의 두 개 거의 없음.
  const dayStart = new Date(start.getFullYear(), start.getMonth(), start.getDate(), 0, 0, 0);
  const dayEnd   = new Date(start.getFullYear(), start.getMonth(), start.getDate(), 23, 59, 59);
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
    if (existing.getLocation() !== loc)     { existing.setLocation(loc);     changed = true; }
    if (existing.getEndTime().getTime() !== end.getTime()) {
      existing.setTime(start, end);
      changed = true;
    }
    if (changed) counters.upd++; else counters.skip++;
  } else {
    if (ev.is_all_day) {
      cal.createAllDayEvent(subject, start);
    } else {
      cal.createEvent(subject, start, end, {
        description: ev.body || '',
        location: ev.location || '',
      });
    }
    counters.new++;
  }
}


// ---------- Helpers ----------

function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj, null, 2))
    .setMimeType(ContentService.MimeType.JSON);
}
