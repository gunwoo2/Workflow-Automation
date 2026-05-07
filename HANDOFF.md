# Life OS ? Handoff (Web �� Local VSCode)

�� ������ Claude Code on the Web ���ǿ��� ������ ���� �۾��� ���� VSCode + Claude Code��
�̰��ϱ� ���� ���ؽ�Ʈ �ڵ�����̴�. �� ���ǿ��� �� ������ ������ �ٷ� �̾� �۾� �����ϴ�.

## TL;DR

- **��ǥ**: SAP ������Ʈ 1�ο� Life OS �ý��� ���� (PMO �ڵ�ȭ + ���� �ڻ�ȭ)
- **���� ����**: ��� DB ���� �Ϸ� (15 ��ƼƼ, 4 Tier). ���� ������ web ����ڽ��� �ܺ� ȣ��
  �������� �ߴ�
- **���� �۾�**: ���ÿ��� `setup.py` ���� �� ��ǿ� 10�� DB �ϰ� ���� (Phase 1 ����)

---

## 1. �۾� ���� �帧 (������ �߳�)

### �Ϸ�
1. ���� ���輭 (`Life_OS_Final_Design.pdf`) �н� ? 48������
2. **���� ������**: ���� �ڵ�ȭ + �ڻ�ȭ�� ���� ���� (�繫/������ �Ŵ����� Phase 4 ����)
3. **�ιڽ� ä�� īŻ�α�**: 8 ī�װ��� �� 20�� ä�� ���� + ������Ʈ�� ���� ä�� ���� ���
4. **OpenClaw vs Hermes vs ��� �ιڽ� ���� �и�**:
   - OpenClaw = ä�� ����Ʈ���� (�з� �� ��)
   - Hermes = �γ� + ��� ��� (raw�� SQLite Episodic Archive)
   - ��� �ιڽ� = ����� �Ŵ��佺Ʈ + audit trail
5. **������ ��ƼƼ ����**: 15�� (Tier 0/0.5/1/2/3/ALL)
6. **Ű ���� ���� 1**: PK �ڵ� ü�� Ȯ��
7. **Ű ���� ���� 2**: �ܺ� ID ����, Status enum, ������ unique, �ڱ�����/fan-out
8. **`notion-db-spec.md` (729��) �ۼ�** ? ���� ���� �ҽ� (SSoT)

### �̿Ϸ� (ȯ�� �������� �ߴ�)
- `.notion/setup.py` (DB �ϰ� ���� ��ũ��Ʈ)
- `.notion/seed_data.py` (SAP Module 19�� + Business Area 30��+)
- ��� DB ���� ����

### ȯ�� ���� �̽�
- **api.notion.com ����**: web ����ڽ� allowlist ������ �� ���� API ȣ�� �Ұ�
- **git push ����**: ���Ͻ� �ڰ����� read-only �� ���� Ŀ�Ը� ���� (1�� ��Ǫ��)
- ���� VSCode + Claude Code ����ũ�� �ۿ����� �� �� �ذ��

---

## 2. �ٽ� ���� ���� (���� ������� �� ��)

### 2.1 ���� ����
- **����**: PMO �ڵ�ȭ (������Ʈ/�۾�/ȸ��/����ũ/���⹰) + �ڻ�ȭ (Cases/Errors/Resources/Templates)
- **���� (Phase 4+)**: �繫 �ý���, ������ �Ŵ��� (���� ����/����/����ó)
- **�͸�ȭ ����Ʈ**: OFF (�Ǹ� ���� ��� ? ����� ����)

### 2.2 Ű ���� ? A�� ��� ä��
- **KD1**: Project �ڵ忡 ȸ�� ���� �� ���� (`PRJ-2026-001`) �� ȸ�� ���� ������
- **KD2**: Tier 2 �ڽ��� Project prefix ��� (`PRJ-2026-001-T-0042`)
- **KD3**: Cases�� �ð迭 PK (`CASE-202605-007`) �� 5�� ���� �� �˻� ȿ��
- **KD4**: SAP Module�� ǥ�� �ڵ� �״�� PK (`FI`, `CO`) + aliases ����
- **KD5**: enum codeval�� ���� snake_case + Hermes ���� ���̺�
- **KD6**: ��� ��ƼƼ�� `external_refs` JSON ���� (Ȯ�强)
- **KD7**: Inbox routed_to_* 11�� �и� �ʵ� (��� �Ѱ� ��ȸ)
- **KD8**: file_hash�� ���⹰ ���� ���� (Microsoft Graph etag�� ����)
- **KD9**: Person.current_company nullable (���� enrich)

### 2.3 ǥ�� �ʵ� Ʈ���� (��� ��ƼƼ)
- `pk` ? Notion Title (�Һ�)
- `name` ? ����� �д� �̸� (���� ����)
- `description` ? �� ���ؽ�Ʈ

### 2.4 PK ü�� ���
```
CO-NNNN          Company        PE-NNNN          Person
FI/CO/MM/...     SAP Module     BA-XXX-YYY       Business Area
PCH-NNNNNN       Person-Company History
PRJ-YYYY-NNN     Project
[Proj]-T-NNNN    Task           [Proj]-D-NNN     Deliverable
[Proj]-M-YYYYMMDD-NN  Meeting   [Proj]-R-NNN     Risk
CASE-YYYYMM-NNN  Case           ERR-NNNNNN       Error
RES-NNNNNN       Resource       TPL-NNN          Template
IBX-YYYYMMDD-NNNN  Inbox
```

### 2.5 Phase 1 vs Phase 2 ����
- **Phase 1 (10 DB)**: ������ 4 + Project + Tier 2 4�� + Inbox
- **Phase 2 (+5 DB)**: PCH + Tier 3 4�� (Cases/Errors/Resources/Templates)

### 2.6 �õ� ������ (setup.py�� �ϰ� ���)
- **SAP Module 19��**: FI, CO, MM, SD, PP, PI, PS, QM, PM, WM, HCM, Basis, ABAP, BW,
  SuccessFactors, Ariba, S4-Core, FICO (����), SD-LE (����)
- **Business Area ī�װ��� 6 + ���� �ټ�**:
  - `BA-FIN-XXX`: ��ȭȯ��(FX), ����ä��(AR), ����ä��(AP), �ڻ�ȸ��(AA), �Ϲ�ȸ��(GL)
  - `BA-COS-XXX`: ���Ժδ��(IMP), �������(ALC), ��ǰ����(PRC)
  - `BA-PUR-XXX`: �Ϲݱ���(GEN), ���ֱ���(SUB), ���縶����(MM)
  - `BA-SAL-XXX`: ���ְ���(ORD), ����(SHP), û��(BIL)
  - `BA-PRD-XXX`: �����ȹ(PLN), �۾�����(WO), BOM
  - `BA-INT-XXX`: �������̽�(IF), EDI, IDoc

---

## 3. ���� ���� ����

### ����
```
/home/user/Workflow-Automation/
������ Life_OS_Final_Design.pdf   �� ���� ���輭 (48p)
������ Life_OS_Final_Design.docx  �� ���� (���� ����)
������ notion-db-spec.md          �� �� ���� ���� �ҽ� (729��)
������ HANDOFF.md                 �� �� ����
```

### �귣ġ
- �۾� �귣ġ: `claude/explore-repository-xSn4Q`
- Ǫ�� �� �� Ŀ��: `49c64e5 Add notion-db-spec.md (15 entities, 4-tier schema)`
- ���ݿ� �ִ� �귣ġ: `add-life-os-design` (PDF/docx��)

### Ǫ�� ���
���� VSCode���� �޾Ƽ� �׳� `git push` �ϸ� ��. Claude Code ����ũ�� �� / �Ϲ� git Ŭ���̾�Ʈ
��� �۵�.

---

## 4. ?? ���� ? ��� ��ū ��� ������Ʈ

Notion Integration Token�� ���� ���ǿ��� ���� (1Password, .env ��)���� �������ϼ���.
������ �÷��� ä�ð� ������ �ʿ� ���� ���� ��ū ��� ��õ.

������ ID (���� ���� �ƴ�):
```
PARENT_PAGE_ID = 3597221afa4880ce8305cbe42a7468ff
PARENT_PAGE_URL = https://www.notion.so/Life-OS-3597221afa4880ce8305cbe42a7468ff
```

---

## 5. ���� VSCode���� �̾��� �۾� (���� ���� ������Ʈ ��õ)

### ù �޽��� ��õ
```
�� ���� HANDOFF.md �� notion-db-spec.md �а� ���ؽ�Ʈ �ľ�����.

���� �۾�: Phase 1 ��� DB 10�� �ڵ� ���� ��ũ��Ʈ �ۼ�.

�䱸����:
- Python stdlib�� ��� (urllib + json) ? pip ������ ����
- ��� (����� �� ���� DB skip)
- 2-pass: (1) ��� DB ���� (relation ����) �� (2) relation �߰�
- 3-pass: �õ� ������ ���� (SAP Module 19 + Business Area 30+)
- .env���� NOTION_TOKEN, PARENT_PAGE_ID �ε�
- .gitignore�� .env, .notion/db_ids.json �߰�
- .env.example ���ø� Ŀ��

���� ����:
.notion/
  setup.py        ? ���� ��ũ��Ʈ
  schema.py       ? DB ��Ű�� ���� (notion-db-spec.md �ڵ�ȭ)
  seed_data.py    ? �õ� ������
  README.md       ? ���� ���

�۾� �� ��� ��ū ���� �޾Ƽ� setup.py �����ϰ� ��� ����.
```

### ���� �غ� (�����)
1. ��� ��ū ������Ʈ (�� 4��)
2. �� ��ū�� `.env`�� ����:
   ```
   NOTION_TOKEN=��_��ū
   PARENT_PAGE_ID=3597221afa4880ce8305cbe42a7468ff
   ```
3. Python 3.10+ ��ġ Ȯ�� (`python --version` �Ǵ� `py --version`)

### ���� ���� (Claude�� �ڵ� �ۼ� ��)
```powershell
# Windows PowerShell
cd C:\path\to\Workflow-Automation
python .notion\setup.py
```
- ���: ������ 10�� DB ��ũ + `.notion/db_ids.json`�� ID ����
- ��ǿ��� "Life OS" ������ ����� DB���� �ڽ����� ������

### ���� üũ����Ʈ
- [ ] 10�� DB ��� ���� (Company, Person, SAP Module, Business Area, Project, Task,
  Deliverable, Meeting, Risk, Inbox)
- [ ] SAP Module DB�� 19�� row �õ��
- [ ] Business Area DB�� 30��+ row �õ�� (parent_area ���� ����)
- [ ] Project DB���� Task/Deliverable/Meeting/Risk 4�� Relation ���� ����
- [ ] Inbox DB�� routed_to_* 11�� Relation �ʵ� ��� ǥ��
- [ ] Person DB�� current_company Relation �� Company �����

---

## 6. 12�� �ε�� ��ġ

```
[Phase 0] ��� (1��)
[Phase 1] PMO MVP (2~3����)  �� �� ��� DB ����� ���� ������
[Phase 2] ���� �ڻ�ȭ (4~6����)
[Phase 3] ������ �Ŵ��� (7~8����)
[Phase 4] CFO + ��ú��� (9~10����)
[Phase 5] AI ������ (11~12����)
```

### Phase 0 �̿� �׸� (���� ����)
- WSL2 + Docker Desktop ��ġ (M5 ���� �� �ص� ��)
- Telegram Bot ���� (BotFather)
- Notion ���� ���� ? (����)
- GitHub PAT �߱�
- Google Calendar API Ű
- Whisper ���� ��ġ

### Phase 1 �۾� ���� (�� �ڵ���� ��)
1. **��� DB ����** (�� ���ǿ��� ������ �� ��)
2. SOUL.md �丣�ҳ� + ī�Ľ� 4��Ģ �ۼ�
3. ~/.claude/CLAUDE.md �۷ι� ����
4. Telegram �� ��� �ιڽ� ��ũ�÷ο� (n8n)
5. ���ϸ� �긮�� cron (n8n)
6. "��������Ʈ X" �ڵ� �¾� SKILL

---

## 7. ���ذ� �ǻ���� (���� ���ǿ��� ����)

���� ���忡�� ������ �ǻ���� �ܿ� ���� �� ���� �͵�:

### D1. Person-Company History�� ������ �Է� ����
- A. ù ��� �� ������ PCH�� ���� ���� (2�� ������)
- B. PCH�� ���� �߻� �ÿ��� ���� (ȸ�� �� �ٲ�� PCH 0��)
- B���� �ܼ�. Hermes�� Person.current_company ���� ���� �� �ڵ� PCH ����

### D2. ��� �ιڽ��� raw �ؽ�Ʈ ���� ����
- ����: <500�� = description�� ���� / ��500�� = Hermes Episodic Archive ��ũ
- ����: ��Ȯ�� description �ѵ��� ��� API���� ������ (2000�ڰ� �� block �ѵ�)
- setup.py �ۼ� ������ Ȯ�� �ʿ�

### D3. Calendar�� Meeting DB�� ���� vs ����
- ����: Meeting�� `scheduled` ���°� �� Ķ���� �̺�Ʈ
- ����: ȸ�� �ƴ� �ܼ� ���� (���� ���, ������)�� ���? Phase 3 ������ �Ŵ������� ����

### D4. Hermes SKILL ���� ���̺� ��ġ
- enum codeval �� �ѱ��� �� ������ �ʿ�
- �ɼ�: SKILL.md ���� / ���� yaml / Notion DB ��ü���� ����
- ���� Hermes �¾� �� ����

---

## 8. ���� ? ä�� īŻ�α� (Phase 1 �� Phase �ļ�)

���� ���� ���ǵ� �ιڽ� ä�� �켱����:

| Phase | ���� ä�� |
|---|---|
| **Phase 0~1** | Telegram + ��� ���� + Cron |
| Phase 2 | OneDrive + IDE ���� + git commit |
| Phase 3 | ī�� ����ê + Google Calendar ����� + ����/�̹��� |
| Phase �ļ� | Outlook (������Ʈ��) + Teams + Slack |

������Ʈ�� ���� ä�� (Outlook/Teams ��)�� **Project DB�� �ܺ� ID �ʵ�**�� ���� ���� ����:
- `outlook_account`, `outlook_calendar_id`, `teams_workspace_id`, `slack_workspace`,
  `sharepoint_url` �� 9�� named field + `external_refs` JSON

---

## 9. �ٽ� ���� ����

- `notion-db-spec.md` ? DB ��Ű�� ���� ���� �ҽ� (������)
- `Life_OS_Final_Design.pdf` ? ���� ���輭 (48������)

�� �� ���� ������ ���ؽ�Ʈ 100% ���� ����.