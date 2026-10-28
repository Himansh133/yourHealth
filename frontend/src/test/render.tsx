import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../auth";

/** Render the given routes inside the real providers, starting at `path`. */
export function renderAt(path: string, routes: Record<string, ReactElement>) {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          {Object.entries(routes).map(([p, el]) => (
            <Route key={p} path={p} element={el} />
          ))}
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
  return user;
}
