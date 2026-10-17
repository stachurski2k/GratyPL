interface Item {
  thumb: string
  full?: string
}

export function Gallery({ items, alt }: { items: Item[]; alt: string }) {
  if (items.length === 0) return null
  return (
    <div className={`gallery gallery-${Math.min(items.length, 4)}`}>
      {items.map((item, i) => (
        <a key={item.thumb} href={item.full ?? item.thumb} target="_blank" rel="noreferrer">
          <img src={item.thumb} alt={`${alt} – zdjęcie ${i + 1}`} loading="lazy" />
        </a>
      ))}
    </div>
  )
}
