import { Link } from 'react-router-dom'

export function HomePage() {
  return (
    <div className="page home">
      <section className="hero">
        <h1>
          graty<span className="accent">PL</span>
        </h1>
        <p className="lead">
          Porzucone i rozbierane samochody stoją miesiącami na parkingach, podwórkach i przy garażach w Gliwicach,
          Zabrzu i okolicach. Zajmują miejsce, cieknie z nich olej, a nikt nie wie, komu je zgłosić.
        </p>
        <div className="hero-actions">
          <Link to="/zglos" className="button button-primary">
            Zgłoś grata
          </Link>
          <Link to="/mapa" className="button">
            Zobacz mapę
          </Link>
        </div>
      </section>

      <section className="card video-card">
        <video src="/gratypl.mp4" controls preload="metadata" playsInline>
          Twoja przeglądarka nie odtwarza wideo.{' '}
          <a href="/gratypl.mp4">Pobierz film o projekcie</a>.
        </video>
      </section>

      <section className="steps">
        <div className="card step">
          <span className="step-number">1</span>
          <h2>Zrób zdjęcie</h2>
          <p>Sfotografuj porzucone auto i zaznacz na mapie, gdzie stoi. Lokalizację możemy też odczytać ze zdjęcia.</p>
        </div>
        <div className="card step">
          <span className="step-number">2</span>
          <h2>Zgłoszenie trafia na mapę</h2>
          <p>Każde zgłoszenie widać na mapie i w strumieniu postów, więc mieszkańcy widzą skalę problemu.</p>
        </div>
        <div className="card step">
          <span className="step-number">3</span>
          <h2>Raport co tydzień</h2>
          <p>Raz w tygodniu powstaje podsumowanie: ile gratów zgłoszono i gdzie. Z nim łatwiej pójść do straży miejskiej.</p>
        </div>
      </section>

      <p className="notice">
        To jest <strong>wersja demonstracyjna</strong> projektu. Zgłoszenia oznaczone jako „Dane przykładowe” są
        wygenerowane automatycznie i nie dotyczą prawdziwych samochodów.
      </p>
    </div>
  )
}
