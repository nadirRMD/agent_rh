import "./globals.css";

export const metadata = {
  title: "Agent RH",
  description: "Interface Next.js pour interroger l'assistant RH.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
