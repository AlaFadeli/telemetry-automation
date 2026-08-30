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

def save_data(df, laps_by_drivers, out_dir):






if __name__ == "__main__":
    app()
