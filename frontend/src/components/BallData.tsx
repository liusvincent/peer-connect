type BallDataProps = {
  x: number | null;
  y: number | null;
};

function BallData({ x, y }: BallDataProps) {
  return (
    <section>
      <h2>Ball Coordinates </h2>
      <p>X: {x ?? "-"}</p>
      <p>Y: {y ?? "-"}</p>
    </section>
  );
}

export default BallData;
