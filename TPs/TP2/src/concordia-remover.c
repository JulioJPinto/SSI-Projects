#include "../includes/lib.h"
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define BLOCK_SIZE 16

int main(int argc, char *argv[])
{
  if (argc < 2)
  {
    char buffer[100];
    snprintf(buffer, 100, "Usage: %s <id>\n", argv[0]);
    write(1, buffer, strlen(buffer));
    return -1;
  }

  // get username
  char *username = get_username();
  if (username == NULL)
  {
    perror("[ERROR] Couldn't get username");
    return -1;
  }

  // get message file path
  char path[100];
  snprintf(path, 100, "concordia/%s/received/%s", username, argv[1]);

  // remove message file
  execl("/bin/rm", "rm", path, NULL);

  return 0;
}
