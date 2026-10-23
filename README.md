# wp-publish

Publish Markdown pages to a WordPress site through its REST API.

- Each page is listed in a `pages.yml` beside the documents: the file, its slug, its language, a shared key for its translations, and an optional parent page.
- Signs in with a WordPress Application Password kept in a credential file readable only by you.
- Runs as a dry run unless told to publish.
- Records each published page's id by key and language in `published.yml`, ready for pairing translations later.

MIT License.
