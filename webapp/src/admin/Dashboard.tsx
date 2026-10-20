import { api } from "../api";
import { useApp } from "../ctx";
import { fmtTime, nf, usd } from "../format";
import { ErrorBox, Loading, useLoad } from "../ui";
import { BarChart, LineChart, palette } from "./charts";
import { ActivityFeed, ChartCard, Kpi } from "./parts";
import type { ActivityItem, Overview, SeriesData } from "./parts";

interface BotStats {
  users_total: number; users_period: number; started: number; started_period: number; generations_period: number; generations_total: number;
  photo: number; video: number; audio: number; errors_period: number; last_activity: string | null;
  app: { users_total: number; generations_period: number };
}
import { pq, usePeriod } from "./shell";

/** Главная админки: состояние всего Nolla AI за выбранный период. Все числа — из базы. */
export function Dashboard() {
  const { nav } = useApp();
  const { period } = usePeriod();
  const q = pq(period);
  const ov = useLoad(() => api.admin.get<Overview>(`analytics/overview?${q}`), [q]);
  const ser = useLoad(() => api.admin.get<SeriesData>(`analytics/series?${q}`), [q]);
  const act = useLoad(() => api.admin.get<ActivityItem[]>("activity?limit=15"), []);
  const bot = useLoad(() => api.admin.get<BotStats>(`bot-stats?${q}`), [q]);
  if ((ov.loading && !ov.data) || (ser.loading && !ser.data)) return <Loading />;
  if (ov.error || !ov.data) return <ErrorBox message={ov.error ?? "Ошибка"} onRetry={ov.reload} />;
  const o = ov.data, s = ser.data;
  return (
    <>
      <div className="kpi-groups">
        <Kpi title="Пользователи" big={nf(o.users.total)} bigLabel="Всего пользователей" orange rows={[["Новых за период", nf(o.users.new)], ["Активных", nf(o.users.active)], ["Вернувшихся", nf(o.users.returned)]]} />
        <Kpi title="Генерации" big={nf(o.generations.total)} bigLabel="Всего за период" rows={[["Фото", nf(o.generations.photo)], ["Видео", nf(o.generations.video)], ["Успешных", nf(o.generations.success)], ["Ошибок", nf(o.generations.errors)]]} />
        <Kpi title="Деньги" big={`${nf(o.money.revenue_stars)} ⭐`} bigLabel={`Выручка за период ≈ ${usd(o.money.revenue_usd_estimate)} (оценка)`} orange
          rows={[["Сегодня", `${nf(o.money.today)} ⭐`], ["За 7 дней", `${nf(o.money.d7)} ⭐`], ["За 30 дней", `${nf(o.money.d30)} ⭐`], ["Средний чек", `${nf(o.money.avg_check)} ⭐`]]} />
        <Kpi title="Токены" big={nf(o.tokens.balance_total)} bigLabel="Остаток у пользователей" rows={[["Продано", nf(o.tokens.sold)], ["Потрачено", nf(o.tokens.spent)], ["Возвращено", nf(o.tokens.refunded)]]} />
        <Kpi title="Подписки" big={nf(o.subscriptions.pro)} bigLabel="Пользователей с PRO" rows={[["Бесплатные", nf(o.subscriptions.free)], ["Подключено за период", nf(o.subscriptions.granted)], ["Отменено за период", nf(o.subscriptions.cancelled)]]} />
      </div>
      {o.money.other_currencies.length > 0 && <div className="notice info"><p>Другие платёжные системы за период: {o.money.other_currencies.map((c) => `${nf(c.amount)} ${c.currency} (${c.n})`).join(", ")}.</p></div>}
      {s && (
        <div className="charts">
          <ChartCard title="Рост пользователей"><LineChart days={s.days} series={[{ name: "Новые", color: palette.orange, values: s.users_new }, { name: "Активные", color: palette.black, values: s.users_active }, { name: "Вернувшиеся", color: palette.soft, values: s.users_returned }]} /></ChartCard>
          <ChartCard title="Выручка, Stars"><BarChart days={s.days} series={{ name: "Выручка", color: palette.orange, values: s.revenue }} /></ChartCard>
          <ChartCard title="Покупки и средний чек"><LineChart days={s.days} series={[{ name: "Покупок", color: palette.black, values: s.purchases }, { name: "Средний чек, Stars", color: palette.orange, values: s.avg_check }]} /></ChartCard>
          <ChartCard title="Генерации"><LineChart days={s.days} series={[{ name: "Фото", color: palette.orange, values: s.photo }, { name: "Видео", color: palette.black, values: s.video }, { name: "Всего", color: palette.gray, values: s.generations }]} /></ChartCard>
          <ChartCard title="Токены"><LineChart days={s.days} series={[{ name: "Куплено", color: palette.orange, values: s.tokens_bought }, { name: "Потрачено", color: palette.black, values: s.tokens_spent }, { name: "Возвращено", color: palette.soft, values: s.tokens_refunded }]} /></ChartCard>
        </div>
      )}
      {bot.data && (
        <div className="kpi-groups">
          <Kpi title="Бот" big={nf(bot.data.users_total)} bigLabel="Пользователей создавали через бота" orange
            rows={[["Запускали бота", nf(bot.data.started)], ["Активны за период", nf(bot.data.users_period)], ["Последняя активность", bot.data.last_activity ? fmtTime(bot.data.last_activity) : "Нет данных"]]} />
          <Kpi title="Генерации через бота" big={nf(bot.data.generations_total)} bigLabel="Всего через бота"
            rows={[["За период", nf(bot.data.generations_period)], ["Фото", nf(bot.data.photo)], ["Видео", nf(bot.data.video)], ["Аудио", nf(bot.data.audio)], ["Ошибок за период", nf(bot.data.errors_period)]]} />
          <Kpi title="Через приложение" big={nf(bot.data.app.users_total)} bigLabel="Пользователей создавали в приложении"
            rows={[["Генераций за период", nf(bot.data.app.generations_period)]]} />
        </div>
      )}
      <div className="card">
        <div className="card-head"><h2>Последняя активность</h2><button className="link" onClick={() => nav.reset({ name: "admin", page: "activity" })}>Вся активность</button></div>
        {act.data ? <ActivityFeed items={act.data} onUser={(id) => nav.go({ name: "admin", page: "user", id: String(id) })} /> : <Loading />}
      </div>
    </>
  );
}
