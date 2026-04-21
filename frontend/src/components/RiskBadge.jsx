export default function RiskBadge({ risk }) {
  const map = {
    Low:    'bg-green-100 text-green-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    High:   'bg-red-100 text-red-800',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${map[risk] || 'bg-gray-100 text-gray-600'}`}>
      {risk || 'Unknown'}
    </span>
  )
}
