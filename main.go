package main

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/lucasb-eyer/go-colorful"
	"golang.org/x/crypto/ssh/terminal"
)

var baseStyle = lipgloss.NewStyle().
	BorderStyle(lipgloss.NormalBorder()).
	BorderForeground(lipgloss.Color("240"))

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
			Padding(1, 0).
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
				Background(lipgloss.Color("#F25D94")).
				MarginRight(2).
				Underline(true)
				
	docStyle = lipgloss.NewStyle().Padding(1, 2, 1, 2)
)

type item struct {
	title, desc string
}

func (i item) Title() string       { return i.title }
func (i item) Description() string { return i.desc }
func (i item) FilterValue() string { return i.title }

type model struct {
	list         list.Model
	selectedPort string
	activeButton string
}

var doc = strings.Builder{}

func (m model) Init() tea.Cmd {
	renderTitle()
	return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "ctrl+c" {
			return m, tea.Quit
		}
		if msg.String() == "enter" {
			if m.selectedPort == "" {
				port := m.list.SelectedItem().FilterValue()
				m.selectedPort = port
			} else {
				if m.activeButton == "yes" {
					killPort(m)
					m.selectedPort = ""
				}
			}
		}

		// If we reach the dialog to confirm killing a port (and therefore have selected a port)
		if msg.String() == "right" && m.activeButton != "no" {
			m.activeButton = "no"
		}
		if msg.String() == "left" && m.activeButton == "no" {
			m.activeButton = "yes"
		}

	case tea.WindowSizeMsg:
		h, v := docStyle.GetFrameSize()
		m.list.SetSize(msg.Width-h, msg.Height-v)
	}

	var cmd tea.Cmd
	m.list, cmd = m.list.Update(msg)
	return m, cmd
}

func killPort(m model) {
	fmt.Println(m.selectedPort)
}

func (m model) View() string {
	if m.selectedPort != "" {
		return confirmationView(m)
	}
	// doc.WriteString(renderTitle() + "\n\n")
	doc.WriteString(docStyle.Render(m.list.View()))

	return doc.String()
}

func confirmationView(m model) string {
	width, _, _ := terminal.GetSize(0)

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

	qStr := fmt.Sprintf("Are you sure you want to kill port %s", m.selectedPort)
	question := lipgloss.NewStyle().Width(50).Align(lipgloss.Center).Render(qStr)
	buttons := lipgloss.JoinHorizontal(lipgloss.Top, okButton, cancelButton)
	ui := lipgloss.JoinVertical(lipgloss.Center, question, buttons)

	dialog := lipgloss.Place(width, 9,
		lipgloss.Center, lipgloss.Center,
		dialogBoxStyle.Render(ui),
		lipgloss.WithWhitespaceChars(" "),
		lipgloss.WithWhitespaceForeground(subtle),
	)

	return baseStyle.Render(dialog + "\n\n")
}

func main() {
	out, err := exec.Command("lsof", "-i", "-P", "-n", "-sTCP:LISTEN").Output()
	str_stdout := string(out)

	procs := strings.Split(str_stdout, "\n")
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
		fmt.Println(port)

		titleStr := fmt.Sprintf("Port: %s", port)
		descStr := fmt.Sprintf("PID: %s, User: %s, Command: %s", pid, user, command)

		processes = append(processes, item{title: titleStr, desc: descStr})
	}

	if err != nil {
		fmt.Println(err.Error())
	}
	m := model{
		list:         list.New(processes, list.NewDefaultDelegate(), 0, 0),
		selectedPort: "",
		activeButton: "yes",
	}
	m.list.SetStatusBarItemName("process", "processes")
	m.list.SetShowTitle(false)
	p := tea.NewProgram(m)

	if _, err := p.Run(); err != nil {
		fmt.Println("Error running program:", err)
		os.Exit(1)
	}
}

func renderTitle() {
	var (
		colors = colorGrid(1, 5)
		title  strings.Builder
	)

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

	fmt.Println(docStyle.Render(doc.String()))
}

// Via https://github.com/charmbracelet/lipgloss/blob/776c15f0da16d2b1058a079ec6a08a2e1170d721/examples/layout/main.go#L338
func colorGrid(xSteps, ySteps int) [][]string {
	x0y0, _ := colorful.Hex("#F25D94")
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
