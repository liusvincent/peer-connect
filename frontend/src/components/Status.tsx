type StatusProp = {
  status: String;
};

function Status({ status }: StatusProp) {
  return (
    <section>
      <h2>
        Connection Status:
        <span className="status">{status}</span>
      </h2>
    </section>
  );
}

export default Status;
