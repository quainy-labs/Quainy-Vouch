import { AuthScreen } from "../auth/AuthScreen";
import { LoadingScreen } from "../layout/LoadingScreen";
import { WorkspaceShell } from "../layout/WorkspaceShell";
import { useQuainyWorkspaceController } from "../../hooks/useQuainyWorkspaceController";

export function QuainyApp() {
  const controller = useQuainyWorkspaceController();

  if (controller.screen === "auth") {
    return <AuthScreen {...controller.authProps} />;
  }

  if (controller.screen === "loading") {
    return <LoadingScreen {...controller.loadingProps} />;
  }

  return <WorkspaceShell {...controller.workspaceProps} />;
}
