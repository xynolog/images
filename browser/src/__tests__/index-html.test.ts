/**
 * `index.html` is served before any language is chosen, so it names none. The
 * `lang` and `dir` of `<html>` are set when i18next has a language (see
 * `document-language.test.tsx`).
 *
 * Its favicon links name files of the brand submodule's `favicons/`, which
 * `scripts/copy-favicons.js` stages at `/favicons/`; brand/ sits beside the
 * Browser's directory.
 */
import { describe, it, expect } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const html = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8');

describe('index.html', () => {
  it('declares no language', () => {
    const opening = html.match(/<html[^>]*>/);

    expect(opening?.[0]).toBe('<html>');
  });

  it('links only favicons the brand submodule has', () => {
    const favicons = [...html.matchAll(/<link [^>]*href="(\/favicons\/[^"]+)"/g)].flatMap((match) => match.slice(1));

    expect(favicons.length).toBeGreaterThan(0);
    for (const href of favicons) {
      const file = resolve(process.cwd(), '../brand', href.slice(1));
      expect(existsSync(file), `${href}: no ${file}`).toBe(true);
    }
  });
});
