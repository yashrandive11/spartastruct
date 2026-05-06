export interface IUser {
  id: number;
  name: string;
  email: string;
}

export class User implements IUser {
  id: number;
  name: string;
  email: string;

  constructor(id: number, name: string, email: string) {
    this.id = id;
    this.name = name;
    this.email = email;
  }

  toJSON(): IUser {
    return { id: this.id, name: this.name, email: this.email };
  }
}
