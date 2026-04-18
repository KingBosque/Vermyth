#!/usr/bin/env node
import { VermythMcpServer } from "./server.js";

const server = new VermythMcpServer();
void server.runStdio();
