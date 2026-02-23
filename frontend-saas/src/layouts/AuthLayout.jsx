export function AuthLayout({ children }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-agil-bg-main p-4">
      <div className="w-full max-w-md">{children}</div>
    </div>
  )
}
