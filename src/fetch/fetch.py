import typer
from typing import Annotated
import fastf1
import pandas as pd
from pathlib import Path


app = typer.Typer()
@app.command()
def fetch(
    drivers: Annotated[str, typer.Option(help="Comma-separated driver codes, e.g. VER,PER")],
    year: Annotated[int, typer.Option(help="Season year, e.g. 2023")] = 2023,
    round_name: Annotated[str, typer.Option(help="Race name, e.g. 'Spa', 'Monza'")] = "Spa",
    session: Annotated[str, typer.Option(help="Session: Q = qualifying")] = "Q",
    out_dir: Annotated[str, typer.Option(help="Where to save CSVs")] = "data/raw",
    cache_dir: Annotated[str, typer.Option(help="FastF1 cache folder")] = "cache",
):
    """Fetch F1 telemetry via FastF1 and save it as CSVs in <out_dir>.

    Downloads car telemetry (speed, RPM, throttle, brake, gear) and
    lap summaries for the given drivers, then writes raw CSVs for the
    ingest and analysis steps downstream.
    """
    print(f"Fetching {year} {round_name} {session} for: {drivers}")
    main(year, round_name, session, drivers, out_dir, cache_dir)


def load_session(year: int, round_name: str, session: str, cache_dir: str):
    """Load a session from the FastF1 cache, returning the Session object."""
    if fastf1.Cache.get_cache_info()[0] is None:
        fastf1.Cache.enable_cache(cache_dir)
    session_obj = fastf1.get_session(year, round_name, session)
    session_obj.load(laps=True, telemetry=True)
    return session_obj



def select_laps(session, drivers, n_laps=1):
    laps = []
    for driver in drivers :
        driver_laps = session.laps.pick_drivers(driver)
        valid = driver_laps[(driver_laps['Deleted']) == False & (driver_laps['LapTime'].notna())]
        laps.append(valid.nsmallest(n_laps, 'LapTime'))
    return laps


def extract_car_data(laps_by_drivers):
    frames = []
    for driver_laps in laps_by_drivers:
        for i in range(len(driver_laps)):
            lap_obj = driver_laps.iloc[i]
            tele = lap_obj.get_car_data()
            pos = lap_obj.get_pos_data()
            tele = pd.merge_asof(tele.sort_values('Date'),pos[['Date','X','Y']].sort_values('Date'), on='Date', direction='nearest')
            tele['Driver'] = lap_obj['Driver']
            tele['LapNumber'] = lap_obj['LapNumber']
            tele['LapTime']  = lap_obj['LapTime']
            frames.append(tele)
    return pd.concat(frames,ignore_index=True)        

def sanity_checks(df, laps_df):
    assert len(df) > 0, 'DataFrame is empty'
    assert df['Speed'].max() < 400, 'Speed physically impossible'
    assert df['Speed'].min() >= 0, 'Speed physically impossible'
    assert df['RPM'].max() < 15000, 'Rotation per minute physically impossible'
    assert df['RPM'].min() >= 0, 'Rotation per minute physically impossible'
    assert laps_df['LapTime'].notna().all(), 'Nat rows slipped into the data'
    assert df['Driver'].nunique() == 2, 'Expected 2 drivers, got ' + str(df['Driver'].nunique())


def save_data(df, laps_by_drivers, out_dir):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    df.to_csv(Path(out_dir) / 'telemetry.csv', index=False)
    laps_all = pd.concat(laps_by_drivers, ignore_index=True)
    laps_all.to_csv(Path(out_dir) / 'laps.csv', index=False)
    

def main(year, round_name, session, drivers, out_dir, cache_dir):
    session_obj = load_session(year, round_name, session, cache_dir)
    driver_list = drivers.split(',')
    laps = select_laps(session_obj, driver_list)
    df = extract_car_data(laps)
    laps_df = pd.concat(laps, ignore_index=True)
    sanity_checks(df, laps_df)
    save_data(df, laps, out_dir)
    print(f"Saved {len(df)} telemetry rows + {len(laps_df)} laps to {out_dir}")



if __name__ == "__main__":
    app()
