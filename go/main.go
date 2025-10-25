package main

import (
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/log"
	zone "github.com/lrstanley/bubblezone"
	"github.com/lucasb-eyer/go-colorful"
	"golang.org/x/term"
)

var baseStyle = lipgloss.NewStyle()

var (
	subtle     = lipgloss.AdaptiveColor{Light: "#D9DCCF", Dark: "#383838"}
	titleStyle = lipgloss.NewStyle().
			MarginLeft(1).
			MarginRight(5).
			Padding(0, 1).
			Italic(true).
			Foreground(lipgloss.Color("#FFF7DB")).
			SetString("Gruyere")

	descStyle = lipgloss.NewStyle().MarginTop(1)

	infoStyle = lipgloss.NewStyle().
			BorderStyle(lipgloss.NormalBorder()).
			BorderTop(true).
			BorderForeground(subtle)

	// Dialog.
	dialogBoxStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#874BFD")).
			Padding(1, 2).
			BorderTop(true).
			BorderLeft(true).
			BorderRight(true).
			BorderBottom(true)

	buttonStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FFF7DB")).
			Background(lipgloss.Color("#888B7E")).
			Padding(0, 3).
			MarginTop(1).
			MarginRight(2)

	activeButtonStyle = buttonStyle.Copy().
				Foreground(lipgloss.Color("#FFF7DB")).
				Background(lipgloss.AdaptiveColor{Light: "#EE6FF8", Dark: "#EE6FF8"}).
				MarginRight(2).
				Underline(true)

	docStyle = lipgloss.NewStyle().Padding(1, 2, 1, 2)
)

type item struct {
	title string
	desc  string
}

func (i item) Title() string       { return zone.Mark(i.title, i.title) }
func (i item) Description() string { return zone.Mark(i.desc, i.desc) }
func (i item) FilterValue() string { return zone.Mark(i.title, i.title) }

type model struct {
	list         list.Model
	selectedPort string
	activeButton string
	title        string
}

var doc = strings.Builder{}

type tickMsg time.Time

func (m model) Init() tea.Cmd {
	return tickCmd()
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "ctrl+c" {
			return m, tea.Quit
		}

		if msg.String() == "enter" && m.list.SelectedItem() != nil {
			if m.selectedPort == "" {
				port := m.list.SelectedItem().FilterValue()
				m.selectedPort = port
			} else {
				// If accepted killing the port, grab PID + execute killPort()
				if m.activeButton == "yes" {
					execPortKill(&m)
				}
				// In all cases, reset selected port at the end
				m.selectedPort = ""
			}
		}

		// If we reach the dialog to confirm killing a port (and therefore have selected a port)
		if (msg.String() == "right" || msg.String() == "l") && m.activeButton != "no" {
			m.activeButton = "no"
		}
		if (msg.String() == "left" || msg.String() == "h") && m.activeButton == "no" {
			m.activeButton = "yes"
		}

	// Mouse handlers
	case tea.MouseMsg:
		if msg.Type == tea.MouseWheelUp {
			m.list.CursorUp()
			return m, nil
		}

		if msg.Type == tea.MouseWheelDown {
			m.list.CursorDown()
			return m, nil
		}

		if msg.Type == tea.MouseRelease {
			if m.selectedPort == "" {
				for i, listItem := range m.list.VisibleItems() {
					item, _ := listItem.(item)
					// Check each item to see if it's in bounds.
					if zone.Get(item.title).InBounds(msg) || zone.Get(item.desc).InBounds(msg) {
						// If so, select it in the list.
						m.list.Select(i)
						port := m.list.Items()[i].FilterValue()
						m.selectedPort = port
						break
					}
				}
				// If ok is clicked
			} else if zone.Get("ok").InBounds(msg) {
				execPortKill(&m)
				m.selectedPort = ""
				// If no is clicked
			} else if zone.Get("no").InBounds(msg) {
				m.selectedPort = ""
			}
		}

	case tickMsg:
		cmd := m.list.SetItems(getProcesses())
		return m, tea.Batch(tickCmd(), cmd)

	case tea.WindowSizeMsg:
		h, v := docStyle.GetFrameSize()
		m.list.SetSize(msg.Width-h, msg.Height-v)
	}

	var cmd tea.Cmd
	m.list, cmd = m.list.Update(msg)
	return m, cmd
}

func (m model) View() string {
	var view string
	// If there's a selected port, render the confirmation dialog
	if m.selectedPort != "" {
		view = confirmationView(m)
	} else {
		// Otherwise, we just show the list of processes
		m.list.SetHeight(20)
		view = docStyle.Render(m.list.View())
	}

	return zone.Scan(lipgloss.JoinVertical(lipgloss.Top, m.title, view))
}

func main() {
	// init mouse support via zone
	zone.NewGlobal()

	// Get processes running on listening ports
	processes := getProcesses()

	//Initialize the model
	m := model{
		list:         list.New(processes, list.NewDefaultDelegate(), 0, 0),
		selectedPort: "",
		activeButton: "yes",
	}

	m.list.SetStatusBarItemName("process", "processes")
	//Hide default list title + styles
	m.list.SetShowTitle(false)
	mwheel :=
		key.NewBinding(
			key.WithKeys("mwheel"),
			key.WithHelp("mwheel", "up/down"),
		)
	m.list.AdditionalShortHelpKeys = func() []key.Binding {
		return []key.Binding{
			mwheel,
		}
	}
	m.list.AdditionalFullHelpKeys = func() []key.Binding {
		return []key.Binding{
			mwheel,
		}
	}
	m.title = initTitle()

	// Let 'er rip
	// Note: WithAltScreen is needed or zone(mouse support) will break
	// See https://github.com/lrstanley/bubblezone/issues/11
	p := tea.NewProgram(m, tea.WithAltScreen(), tea.WithMouseCellMotion())

	if _, err := p.Run(); err != nil {
		log.Fatal("Error running program:", err)
		os.Exit(1)
	}
}

// Used to refresh the running processes on listening ports in the list view
func tickCmd() tea.Cmd {
	return tea.Tick(time.Second*1, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func getProcesses() []list.Item {
	out, err := exec.Command("lsof", "-i", "-P", "-n", "-sTCP:LISTEN").Output()
	// Guard to just return empty list on exit error
	if err != nil {
		return []list.Item{}
	}

	strStdout := string(out)

	procs := strings.Split(strStdout, "\n")
	var processes []list.Item
	for i, proc := range procs {
		if len(proc) == 0 || i == 0 {
			continue
		}
		pieces := strings.Fields(proc)
		pid := pieces[1]
		user := pieces[2]
		port := strings.Split(pieces[8], ":")[1]
		command := pieces[0]

		titleStr := fmt.Sprintf("Port :%s (%s)", port, pid)
		descStr := fmt.Sprintf("User: %s, Command: %s", user, command)

		processes = append(processes, item{title: titleStr, desc: descStr})
	}

	return processes
}

func killPort(pid string) {
	pidInt, err := strconv.Atoi(pid)
	if err != nil {
		log.Error("Could not convert to process pid to int - ", err)
	}

	if err := syscall.Kill(pidInt, syscall.SIGKILL); err != nil {
		log.Error("Could not kill process - ", err)
	}
}

func confirmationView(m model) string {
	width, _, _ := term.GetSize(0)
	var okButton, cancelButton string

	if m.activeButton == "yes" {
		okButton = activeButtonStyle.Render("Yes")
		cancelButton = buttonStyle.
			Render("No, take me back")
	} else {
		okButton = buttonStyle.Render("Yes")
		cancelButton = activeButtonStyle.
			Render("No, take me back")
	}

	qStr := fmt.Sprintf("Are you sure you want to kill port %s?", m.selectedPort)
	question := lipgloss.NewStyle().Width(50).Align(lipgloss.Center).Render(qStr)
	buttons := lipgloss.JoinHorizontal(lipgloss.Top, zone.Mark("ok", okButton), zone.Mark("no", cancelButton))
	ui := lipgloss.JoinVertical(lipgloss.Center, question, buttons)

	dialog := lipgloss.Place(width, 9,
		lipgloss.Left, lipgloss.Center,
		dialogBoxStyle.Render(ui),
		lipgloss.WithWhitespaceChars(" "),
		lipgloss.WithWhitespaceForeground(subtle),
	)

	return baseStyle.Render(dialog + "\n\n")
}

func initTitle() string {
	colors := colorGrid(1, 5)
	var title strings.Builder

	for i, v := range colors {
		const offset = 2
		c := lipgloss.Color(v[0])
		fmt.Fprint(&title, titleStyle.Copy().MarginLeft(i*offset).Background(c))
		if i < len(colors)-1 {
			title.WriteRune('\n')
		}
	}

	desc := lipgloss.JoinVertical(lipgloss.Left,
		descStyle.Render("A tiny program for viewing + killing ports"),
		infoStyle.Render("Here's what's running..."),
	)

	row := lipgloss.JoinHorizontal(lipgloss.Top, title.String(), desc)
	doc.WriteString(row + "\n\n")

	return docStyle.Render(doc.String())
}

// Via https://github.com/charmbracelet/lipgloss/blob/776c15f0da16d2b1058a079ec6a08a2e1170d721/examples/layout/main.go#L338
func colorGrid(xSteps, ySteps int) [][]string {
	x0y0, _ := colorful.Hex("#EE6FF8")
	x1y0, _ := colorful.Hex("#EDFF82")
	x0y1, _ := colorful.Hex("#643AFF")
	x1y1, _ := colorful.Hex("#14F9D5")

	x0 := make([]colorful.Color, ySteps)
	for i := range x0 {
		x0[i] = x0y0.BlendLuv(x0y1, float64(i)/float64(ySteps))
	}

	x1 := make([]colorful.Color, ySteps)
	for i := range x1 {
		x1[i] = x1y0.BlendLuv(x1y1, float64(i)/float64(ySteps))
	}

	grid := make([][]string, ySteps)
	for x := 0; x < ySteps; x++ {
		y0 := x0[x]
		grid[x] = make([]string, xSteps)
		for y := 0; y < xSteps; y++ {
			grid[x][y] = y0.BlendLuv(x1[x], float64(y)/float64(xSteps)).Hex()
		}
	}

	return grid
}

func execPortKill(m *model) {
	rgx := regexp.MustCompile(`\((.*?)\)`)
	pid := rgx.FindStringSubmatch(m.list.SelectedItem().FilterValue())[1]
	killPort(pid)
	// Get running processes again when a process is killed
	m.list.SetItems(getProcesses())
	m.list.ResetFilter()
}
