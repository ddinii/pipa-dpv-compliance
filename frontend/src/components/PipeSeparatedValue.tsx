interface PipeSeparatedValueProps {
  value: string
}

// Display only: a value holding several `|`-joined URIs is shown one per line.
// The original string is never modified; a single value renders as plain text.
export function PipeSeparatedValue({ value }: PipeSeparatedValueProps) {
  const parts = value.includes('|')
    ? value.split('|').map((part) => part.trim()).filter((part) => part !== '')
    : []
  if (parts.length < 2) {
    return <>{value}</>
  }
  return (
    <ul className="pipe-values">
      {parts.map((part, index) => (
        <li key={index}>{part}</li>
      ))}
    </ul>
  )
}
