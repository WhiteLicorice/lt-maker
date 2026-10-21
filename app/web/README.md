# The browser build's page

What the browser version of a game runs, besides the engine: `app/utilities/web_export.py` packs `main.py`, `page.js` and `bench.py` beside the engine and the project, and serves the images beside `index.html`.

`pygbag_default.tmpl` is pygbag's own page, unchanged, as pygbag 0.9.3 fetches it from https://pygame-web.github.io/cdn/0.9.3/default.tmpl. `web_export.page_html` fills it in and patches it. To upgrade pygbag, replace it with the new version's file from its CDN folder, set `PYGBAG_VERSION` in `web_export.py`, and check each patch there still finds what it replaces (the build stops if one doesn't).

pygbag is under the MIT License:

> MIT License
>
> Copyright (c) 2022 pygame-web
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.
