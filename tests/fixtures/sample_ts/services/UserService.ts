import { User, IUser } from '../models/User';

export class UserService {
  private users: User[] = [];

  async getAll(): Promise<User[]> {
    return this.users;
  }

  async getById(id: number): Promise<User | undefined> {
    return this.users.find(u => u.id === id);
  }

  async create(data: IUser): Promise<User> {
    const user = new User(data.id, data.name, data.email);
    this.users.push(user);
    return user;
  }

  async delete(id: number): Promise<void> {
    this.users = this.users.filter(u => u.id !== id);
  }
}
