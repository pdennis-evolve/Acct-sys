import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import client from "../../api/client";

const PROVIDER_LABELS = { microsoft: "Microsoft 365", google: "Google Workspace" };

const CALLBACK_ERRORS = {
  not_configured: "This provider is not configured for this environment.",
  invalid_state: "The connection attempt could not be verified. Please try again.",
  exchange_failed: "Could not complete the connection with the provider. Please try again.",
  missing_code: "The provider did not return an authorization code.",
  unknown_provider: "Unknown provider.",
};

export default function Integrations() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [integrations, setIntegrations] = useState(null);
  const [connectError, setConnectError] = useState("");
  const [banner, setBanner] = useState("");

  useEffect(() => {
    load();
    const connected = searchParams.get("connected");
    const error = searchParams.get("error");
    if (connected) setBanner(`${PROVIDER_LABELS[connected] || connected} connected successfully.`);
    if (error) setBanner(CALLBACK_ERRORS[error] || "The connection attempt failed.");
    if (connected || error) setSearchParams({}, { replace: true });
  }, []);

  function load() {
    client.get("/settings/integrations").then((res) => setIntegrations(res.data.integrations));
  }

  async function handleConnect(provider) {
    setConnectError("");
    try {
      const res = await client.get(`/settings/integrations/${provider}/connect`);
      window.location.href = res.data.authorize_url;
    } catch (err) {
      setConnectError(err.response?.data?.error || "Could not start the connection.");
    }
  }

  async function handleDisconnect(provider) {
    await client.delete(`/settings/integrations/${provider}`);
    load();
  }

  if (!integrations) return <div className="page-loading">Loading...</div>;

  return (
    <div>
      <h1>Integrations</h1>
      <p className="text-muted">
        Connect your own Microsoft 365 or Google account so invoices email out as you, not a shared address.
      </p>

      {banner && <div className="auth-success">{banner}</div>}
      {connectError && <div className="auth-error">{connectError}</div>}

      {["microsoft", "google"].map((provider) => {
        const info = integrations[provider];
        return (
          <div className="card" key={provider}>
            <div className="page-header">
              <h2>{PROVIDER_LABELS[provider]}</h2>
              {info.connected ? (
                <span className="badge badge-paid">Connected</span>
              ) : info.configured ? (
                <span className="badge badge-inactive">Not Connected</span>
              ) : (
                <span className="badge badge-void">Not Configured</span>
              )}
            </div>

            {info.connected && <p>Sending as <strong>{info.email_address}</strong></p>}

            {!info.configured && (
              <p className="text-muted">
                This environment has no {PROVIDER_LABELS[provider]} OAuth client credentials on file.
                An administrator must register an app and configure the client ID/secret before this can be connected.
              </p>
            )}

            <div className="button-row">
              {info.connected ? (
                <button type="button" className="btn-secondary" onClick={() => handleDisconnect(provider)}>
                  Disconnect
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-primary"
                  disabled={!info.configured}
                  onClick={() => handleConnect(provider)}
                >
                  Connect {PROVIDER_LABELS[provider]}
                </button>
              )}
            </div>
          </div>
        );
      })}

      <div className="card">
        <div className="page-header">
          <h2>Authorize.net (Customer Portal Payments)</h2>
          {integrations.authorize_net.configured ? (
            <span className="badge badge-paid">Configured</span>
          ) : (
            <span className="badge badge-void">Not Configured</span>
          )}
        </div>
        <p className="text-muted">
          {integrations.authorize_net.configured
            ? "A merchant account is on file. Online invoice payments from the customer portal are reconciled automatically via webhook."
            : "No Authorize.net merchant account is configured for this environment. Customers cannot pay invoices online from the portal until an administrator supplies merchant credentials."}
        </p>
      </div>
    </div>
  );
}
