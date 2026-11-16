export default function ClipStack({ colors, className = '' }: {
  colors?: readonly [string, string, string];
  className?: string;
}) {
  return <svg className={className} viewBox="0 0 60 60" fill="none" aria-hidden="true" focusable="false">
    <g strokeWidth="4" strokeLinejoin="round">
      <path d="M11 19H9Q3 19 3 25V51Q3 57 9 57H35Q41 57 41 51V49" stroke={colors?.[2] || 'currentColor'} />
      <path d="M19 11H17Q11 11 11 17V43Q11 49 17 49H43Q49 49 49 43V41" stroke={colors?.[1] || 'currentColor'} />
      <rect x="19" y="3" width="38" height="38" rx="6" stroke={colors?.[0] || 'currentColor'} />
    </g>
  </svg>;
}
