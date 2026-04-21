export default function ErrorBanner({ message }) {
  return (
    <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
      ⚠️ {message || 'Something went wrong. Is the API running?'}
    </div>
  )
}
