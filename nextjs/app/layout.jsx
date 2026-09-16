import "./globals.css";

export const metadata = {
  title: "Digital Wellbeing Tracker — Make room for life",
  description: "Understand your screen time with Digital Wellbeing Tracker, a local Windows desktop app for application usage, limits, and reminders.",
};

export const viewport = { themeColor: "#f6f5ef" };

export default function RootLayout({ children }) {
  return <html lang="en"><body>{children}</body></html>;
}
