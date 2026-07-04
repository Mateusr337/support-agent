# Agent manual test cases

Corpus: `rag-docs/service_guide.pdf` (OMEN 17.3" Gaming Laptop) and `rag-docs/user_guide.pdf` (HP ENVY 6000 All-in-One).

Run ingest before testing:

```bash
docker compose exec backend python -m app.scripts.ingest_documents --force
```

Pass criteria:

- Correct source document cited or retrieved
- Key facts present in the assistant reply
- Test 10 must not hallucinate cross-product steps

---

## 1. Laptop overheating / safe use

**Question:** Can I use my OMEN laptop on my bed or lap for long gaming sessions?

**Expected source:** `service_guide.pdf` (Safety warning)

**Answer must include:**

- Do not place on lap or block air vents
- Use on a hard, flat surface
- Avoid soft surfaces (pillows, rugs, clothing) blocking airflow
- AC adapter should not contact skin or soft surfaces during operation

---

## 2. Customer Self-Repair vs authorized service

**Question:** Can I replace the SSD on my OMEN 17 laptop myself?

**Expected source:** `service_guide.pdf` (Customer Self-Repair, SSD procedure)

**Answer must include:**

- Some parts are Customer Self-Repair; others are authorized service provider only
- SSD replacement is documented under Customer Self-Repair
- Wrong parts can damage the computer or void warranty
- High-level steps: prepare for disassembly, remove bottom cover, disconnect battery cable, remove SSD

---

## 3. Laptop battery specs

**Question:** What battery does the OMEN 17.3 gaming laptop use?

**Expected source:** `service_guide.pdf` (Product description / spare parts)

**Answer must include:**

- 6 cell, 83 Whr polymer battery
- HP Fast Charge Technology
- Spare part P04861-001 (optional detail)

---

## 4. Laptop memory upgrade

**Question:** How much RAM can I install and what type does the OMEN laptop support?

**Expected source:** `service_guide.pdf` (Product description, Memory modules)

**Answer must include:**

- Two SODIMM slots, dual-channel
- DDR5-5600, 1.1 V
- Supported configs: 16 GB (8×2) and 32 GB (16×2)
- Memory is customer accessible / upgradeable
- Handle module by edges only; use ESD-safe container

---

## 5. Laptop security feature

**Question:** Does the OMEN laptop support TPM for security?

**Expected source:** `service_guide.pdf` (Product description)

**Answer must include:**

- Firmware Trusted Platform Module (TPM) 2.0
- Camera privacy cover (bonus if retrieved)

---

## 6. Printer Wi-Fi reset / setup mode

**Question:** How do I reset Wi-Fi on my HP ENVY 6000 and put it in setup mode again?

**Expected source:** `user_guide.pdf` (Buttons, Connect)

**Answer must include:**

- Press and hold Wi-Fi button on the back for at least 3 seconds
- Restores network settings to default
- Puts printer in Auto Wireless Connect (AWC) setup mode
- Use HP Smart app to complete setup
- Purple edge lighting indicates Wi-Fi setup / waiting for HP Smart (optional)

---

## 7. Printer Quiet Mode

**Question:** How do I make my HP ENVY 6000 print more quietly?

**Expected source:** `user_guide.pdf` (Quiet Mode)

**Answer must include:**

- Turn on Quiet Mode (off by default)
- Slows printing to reduce noise without affecting print quality
- Works for Better quality on plain paper
- Can be changed via HP Smart app or embedded web server

---

## 8. Printer Auto-Off behavior

**Question:** Why does my HP ENVY 6000 turn off by itself after a while?

**Expected source:** `user_guide.pdf` (Auto-Off)

**Answer must include:**

- Auto-Off shuts printer off after 2 hours of inactivity
- Must press Power button to turn back on
- Behavior depends on connection type (wireless, Wi-Fi Direct, USB, Ethernet, fax)
- If Auto-Off disabled, printer enters Energy Save Mode after 5 minutes

---

## 9. Printer diagnostic reports

**Question:** How can I print a wireless network test report from the printer control panel?

**Expected source:** `user_guide.pdf` (Print reports)

**Answer must include:**

- Hold Information button ~3 seconds to light all buttons (for some reports)
- Wireless Network Test Report + Network Configuration Page: press Information + Wi-Fi together
- Report shows wireless diagnostics, signal strength, detected networks

---

## 10. Cross-product / out-of-scope (negative test)

**Question:** How do I replace the printhead on my OMEN gaming laptop?

**Expected source:** None, or partial context only

**Answer must:**

- Not invent laptop printhead replacement steps
- Clarify OMEN doc is a laptop service guide, not a printer
- Optionally redirect printer ink/cartridge topics to ENVY 6000 user guide
- Or state no relevant documents were found if retrieval is weak

---

## Scoring

| Criterion | Target |
|-----------|--------|
| Correct source | ≥ 8/10 |
| Key facts present | ≥ 7/10 |
| No hallucination on test 10 | Required |
