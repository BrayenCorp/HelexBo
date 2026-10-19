import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import { Cover, ErrorBox, Loading, categoryIcon, useLoad } from "../ui";

/** «Создать» — витрина возможностей: категории с примерами. Запуск генерации — кнопкой «+». */
export function Explore() {
  const { nav } = useApp();
  const q = useLoad(() => api.categories(), []);
  return (
    <>
      <div className="head-text">
        <h1>Что хотите создать?</h1>
        <p className="muted">Выберите категорию и найдите свой стиль</p>
      </div>
      {q.loading && !q.data && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      <div className="cat-grid">
        {(q.data ?? []).map((c, i) => (
          <button key={c.id} className="cat" onClick={() => nav.go({ name: "category", id: c.id })}>
            <Cover url={c.cover_url} seed={i} />
            <span className="cat-info">
              <span className="cat-icon"><Icon name={categoryIcon(c.id)} size={20} /></span>
              <span className="cat-text"><b>{c.title}</b><span>{c.description}</span></span>
            </span>
          </button>
        ))}
      </div>
    </>
  );
}
