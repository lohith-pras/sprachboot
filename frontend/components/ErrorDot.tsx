interface Props {
  count: number
  onClick?: () => void
}

export default function ErrorDot({ count, onClick }: Props) {
  return (
    <button
      className="error-dot"
      onClick={onClick}
      aria-label={`${count} error${count !== 1 ? 's' : ''} — click to review corrections`}
      title="Click to see corrections"
      type="button"
    >
      {count}
    </button>
  )
}
