### Hi there 👋

Want your own awesome profile page? Check out [markscribe](https://github.com/muesli/markscribe)!

#### 📌 Pinned Repositories
<!-- PINNED_REPOS -->

#### 🌱 Check out what I'm currently working on
{{range recentContributions 7}}
- [{{.Repo.Name}}]({{.Repo.URL}}) - {{.Repo.Description}} ({{humanize .OccurredAt}})
{{- end}}

#### 🔭 Latest releases I've contributed to
{{range recentReleases 10}}
- [{{.Name}}]({{.URL}}) ([{{.LastRelease.TagName}}]({{.LastRelease.URL}}), {{humanize .LastRelease.PublishedAt}}) - {{.Description}}
{{- end}}

#### ⚡ My recent blog posts
{{range rss "https://guysoft.wordpress.com/feed/" 5}}
- [{{.Title}}]({{.URL}}) ({{humanize .PublishedAt}})
{{- end}}

#### 💬 Feedback

You are more than welcome to contact me :)

#### 📫 How to reach me

- Fediverse: https://hayu.sh/@guysoft
- Twitter: https://twitter.com/guysoft
- Blog: https://guysoft.wordpress.com
