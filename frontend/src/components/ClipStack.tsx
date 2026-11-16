export default function ClipStack({ colors, className = '' }: {
  colors?: readonly [string, string, string];
  className?: string;
}) {
  return <svg className={className} viewBox="0 0 60 60" fill="none" aria-hidden="true" focusable="false">
    <g strokeWidth="4" strokeLinejoin="miter">
      <path d="M11 19H3V57H41V49" stroke={colors?.[2] || 'currentColor'} />
      <path d="M19 11H11V49H49V41" stroke={colors?.[1] || 'currentColor'} />
      <rect x="19" y="3" width="38" height="38" stroke={colors?.[0] || 'currentColor'} />
    </g>
  </svg>;
}
