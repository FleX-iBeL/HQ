// Where the roadmap is (phase M, M1, 10 October 2026): HQ is the app; the user's own files are in
// HQ/workspace (it can be a link to a folder elsewhere), never in the HQ repo. The same
// as routine/hqpaths.py: HQ_ROADMAP wins, else HQ_WORKSPACE (or HQ/workspace)/HQ/roadmap.md.
import { realpathSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const HQ = join(dirname(fileURLToPath(import.meta.url)), '..');
export const WORKSPACE = process.env.HQ_WORKSPACE || join(HQ, 'workspace');
let folder = WORKSPACE;
try { folder = realpathSync(WORKSPACE); } catch {}
export const FOLDER = folder;
export const ROADMAP = process.env.HQ_ROADMAP || join(FOLDER, 'HQ', 'roadmap.md');
