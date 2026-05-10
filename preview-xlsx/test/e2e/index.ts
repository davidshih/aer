import * as path from 'path';
import * as fs from 'fs';
import Mocha from 'mocha';

export async function run(): Promise<void> {
  const mocha = new Mocha({ ui: 'bdd', color: false, timeout: 60_000 });
  const here = __dirname;
  for (const f of fs.readdirSync(here)) {
    if (f.endsWith('.test.js')) mocha.addFile(path.join(here, f));
  }
  await new Promise<void>((resolve, reject) => {
    mocha.run((failures) => (failures > 0 ? reject(new Error(`${failures} failed`)) : resolve()));
  });
}
