import { useApp } from "../ctx";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { Mark, PageHeader } from "../ui";

const FEATURES: [IconName, string][] = [
  ["diamond", "Фото и видео с помощью искусственного интеллекта"],
  ["palette", "Готовые стили и свободное описание"],
  ["bolt", "Быстрый путь от идеи к результату"],
  ["clock", "История генераций и избранное"],
  ["shield", "Приватность: исходные фото не хранятся"],
];

export function About() {
  const { nav } = useApp();
  return (
    <>
      <PageHeader title="О нас" onBack={nav.back} />
      <div className="about-card">
        <Mark size={64} />
        <h1>Nolla AI</h1>
        <p className="muted">Premium AI creative studio внутри Telegram</p>
        <ul>{FEATURES.map(([icon, text]) => <li key={text}><Icon name={icon} size={20} /><span>{text}</span></li>)}</ul>
        <span className="muted small">Версия 1.0.0</span>
      </div>
    </>
  );
}
