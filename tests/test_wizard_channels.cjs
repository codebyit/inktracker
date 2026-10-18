// Run with: node --test tests\test_wizard_channels.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const template = fs.readFileSync(
  path.join(__dirname, '..', 'app', 'templates', 'projects', 'wizard.html'), 'utf8',
);
const script = template.match(/<script>\s*([\s\S]*?)<\/script>/i)[1];
const craftModes = ['Flat Raised', 'Pattern Texture', 'Relief Texture', 'Customize Texture'];
const colorChannels = ['W', 'C', 'M', 'Y', 'K', 'GL'];

function makeWizard({ whiteLoaded = 'W', project = null, studio = {} } = {}) {
  const nodes = {
    'wizard-form': { submit() {} },
    'wizard-settings-json': { textContent: JSON.stringify({
      white_loaded: whiteLoaded,
      multi_craft_enabled: true,
      ink: Object.fromEntries(['C', 'M', 'Y', 'K', 'W', 'FW', 'GL'].map(ch => [
        ch, { capacity: 100, price: 50, preprime_ml: 0.1 },
      ])),
    }) },
    'wizard-project-json': { textContent: JSON.stringify(project) },
    'wizard-studio-json': { textContent: JSON.stringify(studio) },
  };
  const context = vm.createContext({
    document: { getElementById: id => nodes[id] ??= {} },
    fetch: async () => ({ json: async () => [] }),
  });
  vm.runInContext(script, context);
  const wizard = context.wizardData();
  wizard.testNodes = nodes;
  return wizard;
}

// Convert VM-realm arrays/objects before comparing them with host-realm values.
const plain = value => JSON.parse(JSON.stringify(value));

for (const mode of craftModes) {
  test(`${mode}: Color Raised exposes and costs White, CMYK and Gloss`, () => {
    const wizard = makeWizard();
    wizard.setCraftMode(mode);
    assert.deepEqual(plain(wizard.activeChannels), colorChannels);
    assert.equal(wizard.inkMode, 'White>CMYK>Gloss Varnish');
    assert.deepEqual(plain(wizard.layerStack).map(layer => layer.name),
      ['White', 'CMYK', 'Gloss Varnish']);
    wizard.inkUsage.W = 2;
    wizard.inkUsage.GL = 3;
    assert.equal(wizard.projectInkMl, 5);
    assert.equal(wizard.projectInkCost, 2.5);
    assert.ok(Math.abs(wizard.primeTotal.ml - 0.6) < 1e-9);
  });

  test(`${mode}: additional faces and flex white use the same channels`, () => {
    const wizard = makeWizard({ whiteLoaded: 'FW' });
    wizard.setCraftMode(mode);
    const face = wizard.makeExtraCraft(0);
    wizard.setExtraCraftMode(face, mode);
    const expected = colorChannels.map(ch => ch === 'W' ? 'FW' : ch);
    assert.deepEqual(plain(wizard.activeChannels), expected);
    assert.deepEqual(plain(wizard.extraFaceChannels(face)), expected);
    wizard.multiCraftEnabled = true;
    wizard.extraCrafts = [face];
    wizard.inkUsage.FW = 2;
    wizard.inkUsage.GL = 3;
    face.inkUsage.FW = 4;
    face.inkUsage.GL = 5;
    const crafts = JSON.parse(wizard.buildCraftsJson());
    assert.deepEqual(crafts.map(craft => craft.ink_usage),
      [{ FW: 2, GL: 3 }, { FW: 4, GL: 5 }]);
  });

  test(`${mode}: legacy projects and templates restore all Color Raised channels`, async () => {
    const legacy = {
      craft_mode: mode, craft_ink_mode: 'Color Raised', ink_mode: 'CMYK',
      ink_usage: { W: 2, GL: 3 },
    };
    const wizard = makeWizard({ project: {
      ...legacy, crafts_json: JSON.stringify([legacy, legacy]),
    } });
    await wizard.init();
    assert.deepEqual(plain(wizard.activeChannels), colorChannels);
    assert.deepEqual(plain(wizard.extraFaceChannels(wizard.extraCrafts[0])), colorChannels);
    assert.equal(wizard.projectInkMl, 10);
    wizard.applyTemplate(legacy);
    assert.deepEqual(plain(wizard.activeChannels), colorChannels);
  });
}

test('Gloss Raised and foil stamping keep their existing channels on every face', () => {
  const wizard = makeWizard();
  for (const mode of craftModes) {
    wizard.setCraftMode(mode);
    const face = wizard.makeExtraCraft(0);
    wizard.setExtraCraftMode(face, mode);
    for (const [subMode, channels] of [['Gloss Raised', ['GL']], ['White (Foil Stamping)', ['W']]]) {
      if (!wizard.availableCraftInkModes.includes(subMode)) continue;
      wizard.setCraftInkMode(subMode);
      wizard.setExtraCraftInkMode(face, subMode);
      assert.deepEqual(plain(wizard.activeChannels), channels);
      assert.deepEqual(plain(wizard.extraFaceChannels(face)), channels);
    }
  }
});

test('Flat and custom layers remain unchanged', () => {
  const wizard = makeWizard();
  assert.deepEqual(plain(wizard.activeChannels), ['C', 'M', 'Y', 'K']);
  wizard.setInkMode('Customize');
  wizard.layerStack = [{ name: 'White', qty: 1 }, { name: 'Gloss Varnish', qty: 1 }];
  assert.deepEqual(plain(wizard.activeChannels), ['W', 'GL']);
});

test('repeated multi-craft edits preserve each face rather than copying the aggregate', async () => {
  let crafts = [
    { variant_name: 'Front', craft_mode: 'Flat', ink_mode: 'White>CMYK', ink_usage: { C: 1, W: 2 } },
    { variant_name: 'Back', craft_mode: 'Flat', ink_mode: 'CMYK>Gloss Varnish', ink_usage: { C: 2, GL: 3 } },
  ];
  for (let edit = 0; edit < 3; edit++) {
    const wizard = makeWizard({ project: {
      name: 'Two faces', units: 1, status: 'Completed', ink_mode: 'White>CMYK',
      ink_usage: { C: 3, W: 2, GL: 3 }, crafts_json: JSON.stringify(crafts),
    } });
    await wizard.init();
    crafts = JSON.parse(wizard.buildCraftsJson());
    assert.deepEqual(crafts.map(craft => craft.ink_usage),
      [{ C: 1, W: 2 }, { C: 2, GL: 3 }]);
  }
});

test('multi-craft projects retain face serialization when the feature is disabled', async () => {
  const wizard = makeWizard({ project: {
    ink_mode: 'CMYK', ink_usage: { C: 3 },
    crafts_json: JSON.stringify([
      { ink_usage: { C: 1 } }, { ink_usage: { C: 2 } },
    ]),
  } });
  wizard.multiCraftFlag = false;
  await wizard.init();
  assert.deepEqual(JSON.parse(wizard.buildCraftsJson()).map(craft => craft.ink_usage),
    [{ C: 1 }, { C: 2 }]);
});

test('preview and submitted aggregate sum all active faces without pre-prime COGS', () => {
  const wizard = makeWizard();
  wizard.cfg.machine = { purchase_price: 1000, setup_cost: 0, lifespan_hours: 1000,
    annual_hours: 100, power_watts: 100, electricity_rate: 1, annual_maintenance: 10 };
  wizard.cfg.labor = { hourly_rate: 10, overhead_pct: 25 };
  wizard.printH = 2;
  wizard.handsM = 30;
  wizard.units = 2;
  wizard.setInkMode('White>CMYK');
  wizard.inkUsage = { C: 2, W: 1, GL: 90 };
  const face = wizard.makeExtraCraft(0);
  face.inkMode = 'CMYK>Gloss Varnish';
  face.inkUsage = { C: 3, GL: 4, W: 80 };
  wizard.multiCraftEnabled = true;
  wizard.extraCrafts = [face];
  wizard.bomItems = [{ name: 'Box', qty: 2, unitCost: 3 }];
  assert.deepEqual(plain(wizard.projectInkUsage), { C: 5, W: 1, GL: 4 });
  assert.equal(wizard.projectInkMl, 10);
  assert.equal(wizard.inkCost, 5);
  assert.equal(wizard.totalCogs, 23);
  assert.equal(wizard.cogsPerUnit, 11.5);
  assert.ok(Math.abs(wizard.primeTotal.ml - 0.6) < 1e-9);
  wizard.includePreprime = false;
  assert.equal(wizard.primeTotal.ml, 0);
  assert.equal(wizard.totalCogs, 23);
  wizard.submit();
  assert.deepEqual(JSON.parse(wizard.testNodes.ink_usage_json.value), { C: 5, W: 1, GL: 4 });
  assert.deepEqual(JSON.parse(wizard.testNodes.f_crafts_json.value).map(craft => craft.ink_usage),
    [{ W: 1, C: 2 }, { C: 3, GL: 4 }]);
  wizard.multiCraftEnabled = false;
  assert.deepEqual(plain(wizard.projectInkUsage), { W: 1, C: 2 });
});

test('changing mode or white slot drops hidden values from both saved payloads', () => {
  const wizard = makeWizard({ whiteLoaded: 'FW' });
  wizard.setInkMode('White>CMYK>Gloss Varnish');
  wizard.inkUsage = { C: 2, W: 70, FW: 3, GL: 9 };
  wizard.setInkMode('CMYK');
  wizard.submit();
  assert.deepEqual(JSON.parse(wizard.testNodes.ink_usage_json.value), { C: 2 });
  assert.equal(wizard.inkCost, 1);
  wizard.setInkMode('White');
  wizard.submit();
  assert.deepEqual(JSON.parse(wizard.testNodes.ink_usage_json.value), { FW: 3 });
});

test('custom layer faces retain their layers and exclude channels outside the stack', () => {
  const wizard = makeWizard();
  wizard.multiCraftEnabled = true;
  const face = wizard.makeExtraCraft(0);
  face.inkMode = 'Customize';
  face.layerStack = [{ name: 'Gloss Varnish', qty: 1 }];
  face.inkUsage = { GL: 2, C: 100 };
  wizard.extraCrafts = [face];
  const saved = JSON.parse(wizard.buildCraftsJson())[1];
  assert.deepEqual(saved.layer_stack, face.layerStack);
  assert.deepEqual(saved.ink_usage, { GL: 2 });
  assert.equal(wizard.inkCost, 1);
});

for (const qty of [0, '0', '']) {
  test(`BOM quantity ${JSON.stringify(qty)} submits zero, matching its preview`, () => {
    const wizard = makeWizard();
    wizard.bomItems = [{ name: 'Unused box', qty, unitCost: 5 }];
    assert.equal(wizard.bomTotal, 0);
    wizard.submit();
    assert.equal(JSON.parse(wizard.testNodes.bom_json.value)[0].quantity, 0);
  });
}
