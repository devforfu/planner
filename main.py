

def console_login():
    import argparse
    parser = argparse.ArgumentParser(
        description='Connection to MySQL database via console application.')
    parser.add_argument('--host', dest='host', default='localhost')
    parser.add_argument('-u', '--user', dest='user')
    parser.add_argument('-p', '--password', dest='password')
    parser.add_argument('-d', '--database', dest='database')
    args = parser.parse_args()
    return args.host, args.user, args.password, args.database


def main():
    host, user, password = console_login()

if __name__ == '__main__':
    main()