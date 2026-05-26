"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import ChatClient from "./chat-client";
import { AUTH_STORAGE_KEY } from "../lib/auth";

export default function Home() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!window.localStorage.getItem(AUTH_STORAGE_KEY)) {
      router.replace("/login");
      return;
    }

    setReady(true);
  }, [router]);

  if (!ready) {
    return null;
  }

  return <ChatClient />;
}
