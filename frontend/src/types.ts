export type Team = "offense" | "defense";

export interface Player {
  id: string;
  team: Team;
  x: number; // meters
  y: number;
  direction: number | null; // radians, offense only
  is_handler: boolean;
}

export interface ThrowOption {
  receiver_id: string;
  catch_x: number;
  catch_y: number;
  flight_time: number;
  receiver_arrival: number;
  defender_arrival: number;
  defender_id: string | null;
  catch_probability: number;
  yards_gained: number;
  expected_value: number;
  throw_type: "backhand" | "flick" | "hammer" | "scoober";
  outcome:
    | "catch"
    | "block"
    | "incomplete"
    | "out_of_bounds"
    | "interception"
    | "callahan";
  flight_path: [number, number][];
}

export type Scheme = "man" | "zone" | "cup";

export interface SimulateResponse {
  handler_id: string;
  chosen: ThrowOption | null;
  outcome:
    | "catch"
    | "block"
    | "incomplete"
    | "no_throw"
    | "out_of_bounds"
    | "interception"
    | "callahan";
  outcome_detail: string;
  options: ThrowOption[];
  receiver_predicted_positions: Record<string, [number, number]>;
  defender_predicted_positions: Record<string, [number, number]>;
  scheme: Scheme;
}

export const FIELD_LENGTH = 100;
export const FIELD_WIDTH = 37;
export const OFF_ENDZONE_X = 82;
export const DEF_ENDZONE_X = 18;
