class User {
  constructor(id, name, email) {
    this.id = id;
    this.name = name;
    this.email = email;
  }

  toJSON() {
    return { id: this.id, name: this.name, email: this.email };
  }

  static fromRow(row) {
    return new User(row.id, row.name, row.email);
  }
}

module.exports = User;
